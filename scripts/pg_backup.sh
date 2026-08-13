#!/usr/bin/env bash
# Nightly logical backups of every local Postgres database, so an agent (or a
# human) destroying data is an inconvenience, not a catastrophe.
#
# Dumps each non-template database whose name doesn't contain "test" to
#   ~/Backups/postgres/<db>/<db>-<timestamp>.dump   (pg_dump custom format)
# keeping the newest KEEP dumps per database (fewer for the multi-GB racing-api
# — the disk is small, and two known-good generations beat fourteen).
#
# Restore a database:
#   pg_restore --clean --if-exists -d <db> ~/Backups/postgres/<db>/<file>.dump
#
# Installed as a launchd job (com.tomwattley.pg-backup) — see scripts/README
# or `launchctl list | grep pg-backup`.

set -euo pipefail

PATH="/Applications/Postgres.app/Contents/Versions/17/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/Backups/postgres}"
STAMP="$(date +%Y%m%d-%H%M%S)"

_keep_for() {
  case "$1" in
    racing-api) echo 2 ;;  # ~4.7G per dump — two generations is 9.4G
    *) echo 7 ;;
  esac
}

databases=$(psql -d postgres -At -c \
  "SELECT datname FROM pg_database
   WHERE NOT datistemplate AND datname <> 'postgres' AND datname NOT ILIKE '%test%'
   ORDER BY datname")

for db in $databases; do
  dir="$BACKUP_ROOT/$db"
  mkdir -p "$dir"
  pg_dump -Fc -f "$dir/$db-$STAMP.dump" "$db"
  keep="$(_keep_for "$db")"
  ls -t "$dir"/*.dump 2>/dev/null | tail -n +"$((keep + 1))" | while read -r old; do
    rm -f "$old"
  done
  echo "backed up $db ($(du -h "$dir/$db-$STAMP.dump" | cut -f1 | tr -d ' ')), keeping newest $keep"
done
