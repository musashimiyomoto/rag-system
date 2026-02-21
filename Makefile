DOCKER_COMPOSE_FILE := docker-compose.yml
POETRY := $(shell command -v poetry 2>/dev/null || echo $$HOME/.local/bin/poetry)
PYTHON_VERSION := 3.11

GREEN := \033[0;32m
BLUE := \033[0;34m
NC := \033[0m

.PHONY: help install format check test build

help:
	@echo "$(BLUE)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:
	@echo "$(BLUE)Installing poetry...$(NC)"
	curl -sSL https://install.python-poetry.org | python3 -
	@echo "$(GREEN)Poetry installed!$(NC)"

	@echo "$(BLUE)Checking python $(PYTHON_VERSION)...$(NC)"
	@if $(POETRY) python list | grep -q "@$(PYTHON_VERSION)"; then \
		echo "$(GREEN)Python $(PYTHON_VERSION) already installed, skipping.$(NC)"; \
	else \
		echo "$(BLUE)Installing python $(PYTHON_VERSION)...$(NC)"; \
		$(POETRY) python install $(PYTHON_VERSION); \
		echo "$(GREEN)Python $(PYTHON_VERSION) installed!$(NC)"; \
	fi

	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(POETRY) install --with dev,test
	@echo "$(GREEN)Dependencies installed!$(NC)"

	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	$(POETRY) run pre-commit install
	@echo "$(GREEN)Pre-commit hooks setup complete!$(NC)"

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run ruff format .
	$(POETRY) run ruff check --fix .
	@echo "$(GREEN)Formatting completed!$(NC)"

check:
	@echo "$(BLUE)Checking code with ruff...$(NC)"
	$(POETRY) run ruff check .
	@echo "$(GREEN)Ruff check completed!$(NC)"

	@echo "$(BLUE)Checking types with ty...$(NC)"
	$(POETRY) run ty check
	@echo "$(GREEN)Type check completed!$(NC)"

test:
	@echo "$(BLUE)Running tests...$(NC)"
	$(POETRY) run pytest
	@echo "$(GREEN)Tests completed!$(NC)"


build:
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Copying .env.example to .env...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN).env.example to .env copied!$(NC)"; \
	fi

	@echo "$(BLUE)Building project in Docker Compose...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) up --build
	@echo "$(GREEN)Project built!$(NC)"


stop:
	@echo "$(BLUE)Stopping project in Docker Compose...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) down
	@echo "$(GREEN)Project stopped!$(NC)"


.DEFAULT_GOAL := help
