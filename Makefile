.PHONY: install serve web mobile test init-db

install:
	uv sync --project apps/api
	npm install

serve:
	uv run --project apps/api agentic-control-plane serve

web:
	npm --workspace @agentic-control-plane/web run dev

mobile:
	npm --workspace @agentic-control-plane/mobile run start

test:
	uv run --project apps/api pytest apps/api/tests/ -v

init-db:
	uv run --project apps/api agentic-control-plane init-db
