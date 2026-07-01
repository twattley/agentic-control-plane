import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(prog="agentic-control-plane")
    sub = parser.add_subparsers(dest="command")

    serve_p = sub.add_parser("serve", help="Run the FastAPI server")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8400)
    serve_p.add_argument("--reload", action="store_true", default=True)

    sub.add_parser("init-db", help="Apply schema migrations")

    args = parser.parse_args()

    if args.command == "serve":
        reload_flag = ["--reload"] if args.reload else []
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", args.host, "--port", str(args.port)]
            + reload_flag,
            check=True,
        )
    elif args.command == "init-db":
        from app.database import apply_migrations
        apply_migrations()
    else:
        parser.print_help()
