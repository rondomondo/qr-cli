DOCKER_REPO ?= rondomondo
IMAGE       := $(DOCKER_REPO)/qr-cli
TAG         := latest
PROJECT     ?= daveco

.DEFAULT_GOAL := help
SHELL := /bin/bash

BOLD   := \033[1m
CYAN   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

PYTHON   := python3
VENV     := .venv
PIP      := $(VENV)/bin/pip

.PHONY: build build-clean usage shell clean help examples gen-examples skill-examples skill-examples-local skill-install skill-zip demo demo-all
.PHONY: py-install py-install-node py-test py-lint py-build py-publish py-publish-test py-check-backend doctor

help: ## Show this help message
	@printf "$(BOLD)$(IMAGE) -- available targets$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""

.PHONY: check-venv
check-venv: venv ## Verify the virtual environment is activated
	@if [ -z "$${VIRTUAL_ENV:-}" ]; then \
	  printf "\033[31mERROR:\033[0m virtual env not active.\n"; \
	  printf "Activate it first:\n\n"; \
	  printf "  \033[32msource $(VENV)/bin/activate\033[0m\n\n"; \
	  printf "Then re-run make.\n"; \
	  exit 1; \
	fi
	@echo "  venv active: $${VIRTUAL_ENV}"

.PHONY: venv
venv: ## Create Python virtual environment (if absent)
	@if [ ! -d "$(VENV)" ]; then \
	  echo "  creating venv in $(VENV)..."; \
	  $(PYTHON) -m venv $(VENV); \
	  $(VENV)/bin/pip install --upgrade pip; \
	  echo "  venv created - activate with: source $(VENV)/bin/activate"; \
	else \
	  echo "  venv already exists in $(VENV)"; \
	fi


build: ## Build the Docker image
	docker build -t $(IMAGE):$(TAG) .

build-clean: ## Build the Docker image with no layer cache
	docker build --no-cache -t $(IMAGE):$(TAG) .

usage: ## Show the generator's own --help as pretty-printed JSON
	docker run --rm $(IMAGE):$(TAG) --help | python3 -m json.tool

shell: ## Open an interactive bash shell inside the container
	docker run --rm -it --entrypoint bash $(IMAGE):$(TAG)

gen-examples: ## Parse EXAMPLES.md and (re)generate run_examples.sh
	@python3 scripts/extract_examples.py --project $(PROJECT) --image $(IMAGE):$(TAG)

skill-examples-local: ## Parse EXAMPLES.md and print equivalent /qr for local viewing
	@python3 scripts/extract_skill_examples.py

examples: gen-examples ## Parse EXAMPLES.md and run all bash examples
	@printf "$(GREEN)Generating examples$(RESET)\n"
	@bash scripts/run_examples.sh
	@printf "$(BOLD)$(CYAN)Generated images$(RESET)\n"
	@find assets/images -type f | xargs file

skill-examples: ## Parse EXAMPLES.md and print equivalent /qr skill commands
	@python3 .claude/skills/qr/scripts/extract_skill_examples.py
	@$(MAKE) skill-examples-local


skill-install: ## Install the /qr skill into ~/.claude/skills/qr/ with Python fallback support
	@printf "$(GREEN)Installing .claude/skills/qr -> ~/.claude/skills/qr$(RESET)\n"
	@mkdir -p ~/.claude/skills/qr 2> /dev/null
	@chmod +x  .claude/skills/qr/scripts/*
	@/bin/cp -R .claude/skills/qr ~/.claude/skills/
	@pip install -e "."
	@printf "$(GREEN)Installed .claude/skills/qr  -> ~/.claude/skills/qr$(RESET)\n"
	@printf "$(CYAN)Python fallback (Node backend) available via: python3 -m qr_cli$(RESET)\n"

skill-zip: ## Zip .claude/skills/qr/ into .claude/skills/qr.zip
	@printf "$(CYAN)Zipping$(RESET) .claude/skills/qr -> .claude/skills/qr.zip\n"
	@cd .claude/skills && zip -r qr.zip qr/
	@printf "$(GREEN)Written$(RESET) .claude/skills/qr.zip\n"

doctor: ## Show environment info useful for bug reports
	@printf "$(BOLD)qr-cli doctor$(RESET)\n\n"
	@printf "  Shell:          %s\n" "$$SHELL"
	@printf "  Docker:         "; docker --version 2>/dev/null || printf "$(RED)not found$(RESET)\n"
	@printf "  Docker running: "; docker info >/dev/null 2>&1 && printf "$(GREEN)yes$(RESET)\n" || printf "$(RED)no$(RESET)\n"
	@printf "  qr-cli image:   "; docker image inspect $(IMAGE):$(TAG) --format '{{.RepoTags}} ({{.Id}})' 2>/dev/null || printf "not built (run make build)\n"
	@printf "  Python:         "; $(PYTHON) --version 2>/dev/null || printf "$(RED)not found$(RESET)\n"
	@printf "  venv:           "; [ -d "$(VENV)" ] && printf "$(GREEN)present$(RESET)\n" || printf "$(YELLOW)absent (run make venv)$(RESET)\n"
	@printf "  skill installed:"; [ -d ~/.claude/skills/qr ] && printf " $(GREEN)yes$(RESET)\n" || printf " $(YELLOW)no (run make skill-install)$(RESET)\n"
	@echo ""

py-install: venv ## Install qr-cli in editable mode (Docker primary, Node fallback)
	$(PIP) install -e ".[dev]"

py-install-node: py-install ## Pre-install bundled Node deps for the Node backend fallback
	$(VENV)/bin/python -m qr_cli --install

py-test: py-install ## Run Python package tests
	$(VENV)/bin/pytest tests/ -v

py-lint: py-install ## Lint qr_cli/ with ruff
	$(VENV)/bin/ruff check qr_cli/

py-build: py-install ## Build sdist + wheel ready for upload
	$(VENV)/bin/python -m build

py-publish: py-build ## Upload release to PyPI
	$(VENV)/bin/twine upload dist/*

py-publish-test: py-build ## Upload release to TestPyPI
	$(VENV)/bin/twine upload --repository testpypi dist/*

py-check-backend: py-install ## Report which backend qr-cli will use in this environment
	@$(VENV)/bin/python -c "from qr_cli.backends import get_backend; b = get_backend(); print('backend:', b.name)"

clean: ## Remove Docker image, build artifacts, caches, and temp files
	@docker rmi $(IMAGE):$(TAG) 2>/dev/null || true
	@/bin/rm -f scripts/run_examples.sh 2>/dev/null || true
	@find assets/images/$(PROJECT) -mindepth 2 -type f -delete 2>/dev/null || true
	@/bin/rm -rf dist/ build/ qr_cli_py.egg-info/ .venv/ 2>/dev/null || true
	@find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '*.egg-info' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -not -path './.git/*' -delete 2>/dev/null || true
	@find . -type d -name '.mypy_cache' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.ruff_cache' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@/bin/rm -rf deleteme.*/ 2>/dev/null || true


DEMO_PKGS  := make git jq htop curl cpio build-essential docker.io python3 python3-dev python3.13-venv glow vim bash
DEMO_IMAGE := ghcr.io/charmbracelet/vhs
REPO_NAME  := qr-cli
TAPE       ?= demo.tape

DEMO_TAPES := $(wildcard demo/*.tape)

.PHONY: demo demo-all

demo: ## Regenerate terminal demo GIF for TAPE=<file> (default: demo.tape)
	mkdir -p demo
	docker run -it --rm \
		-v $$(pwd):/tmp/src:ro \
		-v $$(pwd)/demo:/output \
		-v /var/run/docker.sock:/var/run/docker.sock \
		--name "vhs-$(REPO_NAME)" \
		--entrypoint sh $(DEMO_IMAGE) \
		-c "apt-get update -qq && apt-get install -y $(DEMO_PKGS) && \
			DEST=/tmp/$(REPO_NAME) && \
			mkdir -p \$$DEST && \
			cd /tmp/src && scripts/list_files.sh | cpio -pdm \$$DEST 2>/dev/null && \
			cd \$$DEST && \
			make clean && \
			make venv && \
			. \$$DEST/.venv/bin/activate && \
			cd \$$DEST/ && \
 			vhs \$$DEST/demo/$(TAPE) && \
 			/bin/cp -f \$$DEST/demo/*.* /output/ 2>/dev/null || true"

demo-all: ## Regenerate terminal demo GIFs for all *.tape files in demo/
	@for tape in $(DEMO_TAPES); do \
		echo ""; \
		printf "$(BOLD)$(CYAN)-- Running $$tape --$(RESET)\n"; \
		$(MAKE) demo TAPE=$$tape || exit 1; \
	done


