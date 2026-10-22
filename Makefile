# Local shortcuts; CI runs the same checks.
.PHONY: install check check-backend check-frontend fix

install:
	cd backend && uv sync
	cd frontend && npm ci

check: check-backend check-frontend

check-backend:
	cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest

check-frontend:
	cd frontend && npm run format:check && npm run lint && npm run typecheck && npm test

fix:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && npm run format && npx eslint --fix .
