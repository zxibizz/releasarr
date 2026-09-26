# Run from the repository root. `make help` lists the targets.

BACKEND  := services/backend
FRONTEND := services/frontend

.DEFAULT_GOAL := help
.PHONY: help setup dev check lint typecheck test test-backend test-frontend build \
        codegen image

help: ## List the targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install backend and frontend dependencies
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm ci

dev: ## Run the API, scheduler and Vite with hot reload in Docker
	docker compose -f docker-compose.dev.yaml up --build

check: lint typecheck test ## Everything CI runs on the code
	python3 .github/scripts/check_version.py

lint: ## ruff, ruff format and eslint
	cd $(BACKEND) && uv run ruff check ./src ./tests && uv run ruff format --check ./src
	cd $(FRONTEND) && npm run lint

typecheck: ## mypy and tsc
	cd $(BACKEND) && uv run mypy src
	cd $(FRONTEND) && npx tsc --noEmit

test: test-backend test-frontend ## Both test suites

test-backend: ## pytest
	cd $(BACKEND) && uv run pytest -q

test-frontend: ## vitest
	cd $(FRONTEND) && npm test

build: ## Production build of the UI
	cd $(FRONTEND) && npm run build

codegen: ## Regenerate the UI's API types from openapi.yaml
	cd $(FRONTEND) && npm run codegen

image: ## Build the production image as releasarr:local
	docker build -t releasarr:local .
