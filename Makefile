.DEFAULT_GOAL := help

.PHONY: help install run test lint fix format check clean dist deb

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Sync dependencies from uv.lock
	uv sync

run: install ## Run the app
	uv run python src/main.py

test: ## Run tests
	uv run pytest

lint: ## Check for lint errors
	uv run ruff check src tests

fix: ## Auto-fix lint errors
	uv run ruff check --fix src tests

format: ## Format source code
	uv run ruff format src tests

check: lint test ## Lint + test (CI gate)

dist: install ## Build PyInstaller onedir under dist/fluffy-toothpaste
	uv run pyinstaller packaging/fluffy.toothpaste.spec --noconfirm

deb: ## Build .deb (runs PyInstaller + dpkg-deb)
	bash packaging/build-deb.sh

clean: ## Remove cache artifacts
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist .deb-staging
