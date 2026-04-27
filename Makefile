.DEFAULT_GOAL := help

VENV := .venv
PIP := $(VENV)/bin/pip
PIP_INSTALL_ARGS ?=
DOCS_DIR ?= docs

.PHONY: .check-venv-exists
.check-venv-exists:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Error: Virtual environment not found. Please run 'make install' first."; \
		exit 1; \
	fi

.PHONY: .check-venv-activated
.check-venv-activated:
	@if [ -z "${VIRTUAL_ENV}" ] || [ "${VIRTUAL_ENV}" != "$(abspath $(VENV))" ]; then \
		echo "Error: Virtual environment not activated. Please run 'source $(VENV)/bin/activate' first."; \
		exit 1; \
	fi

## ---------------------------------------------------------------------------
## Setup
## ---------------------------------------------------------------------------

.PHONY: install
install: ## Install cardano-clusterlib and its dependencies into a virtual environment
	@if [ -n "${VIRTUAL_ENV}" ] && [ "${VIRTUAL_ENV}" != "$(abspath $(VENV))" ]; then \
		echo "Error: Another virtual environment is currently activated. Please deactivate it before running 'make install'."; \
		exit 1; \
	fi
	@if [ ! -x "$(VENV)/bin/python3" ]; then \
		python3 -m venv $(VENV); \
	fi
	$(PIP) install --require-virtualenv --upgrade pip
	$(PIP) install --require-virtualenv --upgrade -r requirements-dev.txt $(PIP_INSTALL_ARGS)
	@echo ""
	@echo "Virtual environment ready. Activate with: source $(VENV)/bin/activate"

## ---------------------------------------------------------------------------
## Linting
## ---------------------------------------------------------------------------

.PHONY: init-lint
init-lint: .check-venv-exists ## Initialize linters
	$(VENV)/bin/pre-commit clean
	$(VENV)/bin/pre-commit gc
	find . -path '*/.mypy_cache/*' -delete
	$(VENV)/bin/pre-commit uninstall
	$(VENV)/bin/pre-commit install --install-hooks

.PHONY: lint
lint: .check-venv-exists ## Run linters
	$(VENV)/bin/pre-commit run -a --show-diff-on-failure --color=always

## ---------------------------------------------------------------------------
## Release
## ---------------------------------------------------------------------------

.PHONY: build
build: .check-venv-exists ## Build package distributions
	$(VENV)/bin/python3 -m build

.PHONY: upload
upload: .check-venv-activated ## Upload package distributions to PyPI
	if ! command -v twine >/dev/null 2>&1; then $(PIP) install --require-virtualenv --upgrade twine; fi
	twine upload --skip-existing dist/*

.PHONY: release
release: build upload ## Build and upload package distributions to PyPI

## ---------------------------------------------------------------------------
## Documentation
## ---------------------------------------------------------------------------

.PHONY: install-doc
install-doc: .check-venv-exists ## Install documentation dependencies into the project virtual environment
	$(PIP) install --require-virtualenv --upgrade -r $(DOCS_DIR)/requirements.txt

.PHONY: doc
doc: .check-venv-activated install-doc ## Build Sphinx documentation
	mkdir -p $(DOCS_DIR)/build
	$(MAKE) -C $(DOCS_DIR) clean
	$(MAKE) -C $(DOCS_DIR) html

## ---------------------------------------------------------------------------
## Maintenance
## ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -not -path './$(VENV)/*' -exec rm -rf {} +
	find . -type d -name .pytest_cache -not -path './$(VENV)/*' -exec rm -rf {} +
	find . -type d -name .mypy_cache -not -path './$(VENV)/*' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -not -path './$(VENV)/*' -exec rm -rf {} +
	find . -name '*.pyc' -not -path './$(VENV)/*' -delete

.PHONY: clean-all
clean-all: clean ## Clean all build artifacts, caches, and virtual environment
	@echo "Removing virtual environment: $(VENV)"
	rm -rf -- "$(VENV)"

## ---------------------------------------------------------------------------
## Help
## ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} \
		/^## [A-Z][a-zA-Z]*$$/ { section = substr($$0, 4); next } \
		/^[a-zA-Z_-]+:.*##/ { \
			if (section != last_section) { \
				printf "\n\033[1m%s\033[0m\n", section; \
				last_section = section; \
			} \
			printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2; \
		}' \
		$(MAKEFILE_LIST)
