.PHONY: help install lint format test check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dev dependencies
	python3 -m pip install -r requirements-dev.txt

lint: ## Run ruff lint and format checks
	ruff check .
	ruff format --check .

format: ## Auto-format with ruff
	ruff format .
	ruff check --fix .

test: ## Run the unit tests
	pytest

check: lint test ## What CI runs: lint + tests
