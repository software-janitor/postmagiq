# ============================================================================
# WORKFLOW ORCHESTRATOR MAKEFILE
# ============================================================================

# CI configuration
TEST_DIRS := tests/unit tests/integration
SRC_DIRS := runner api

# Full CI: lint, build, start services, test, stop
ci-report:
	@echo "=============================================="
	@echo "CI REPORT - $$(date)"
	@echo "=============================================="
	@FAILED=0; \
	\
	echo ""; echo "[1/6] Linting..."; \
	if ruff check $(SRC_DIRS); then echo "✅ Lint passed"; else echo "❌ Lint failed"; FAILED=1; fi; \
	\
	echo ""; echo "[2/6] Format check..."; \
	if ruff format $(SRC_DIRS) --check; then echo "✅ Format passed"; else echo "❌ Format failed"; FAILED=1; fi; \
	\
	echo ""; echo "[3/6] Building GUI..."; \
	if cd gui && npm run build; then echo "✅ GUI build passed"; else echo "❌ GUI build failed"; FAILED=1; fi; \
	cd ..; \
	\
	echo ""; echo "[4/6] Starting services..."; \
	docker compose up -d postgres pgbouncer && sleep 3; \
	docker compose exec postgres pg_isready -U orchestrator || sleep 5; \
	cd runner/db/migrations && DATABASE_URL=postgresql://orchestrator:orchestrator_dev@localhost:5434/orchestrator alembic upgrade head && cd ../../..; \
	uvicorn api.main:app --host 0.0.0.0 --port 8000 & API_PID=$$!; \
	sleep 3; \
	if curl -s http://localhost:8000/health > /dev/null; then \
		echo "✅ API started"; \
	else \
		echo "❌ API failed to start"; FAILED=1; \
	fi; \
	\
	echo ""; echo "[5/6] Running tests..."; \
	if python3 -m pytest $(TEST_DIRS) -v --tb=short; then \
		echo "✅ Tests passed"; \
	else \
		echo "❌ Tests failed"; FAILED=1; \
	fi; \
	\
	echo ""; echo "[6/6] Stopping services..."; \
	kill $$API_PID 2>/dev/null || true; \
	docker compose stop postgres pgbouncer; \
	echo "✅ Services stopped"; \
	\
	echo ""; echo "=============================================="; \
	if [ $$FAILED -eq 0 ]; then \
		echo "🎉 CI PASSED"; exit 0; \
	else \
		echo "❌ CI FAILED"; exit 1; \
	fi

.PHONY: help setup install-hooks install-deps install-gui-deps install-gh check-env \
        workflow workflow-interactive workflow-step list-configs check-config test test-unit test-int test-e2e \
        test-isolation coverage logs log-states log-tokens log-summary clean \
        up up-gpu up-cpu down api gui gui-build dev dev-stop restart ollama-pull ollama-list \
        eval-agents eval-costs eval-trend eval-post eval-summary \
        seed-db seed-db-force seed-voices seed-personas seed-sentiments sync-workflows \
        db-up db-down db-migrate db-rollback db-revision db-history db-current db-migrate-data db-init db-drop db-shell \
        pr ci-report

# Default target
help:
	@echo "Workflow Orchestrator Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup                               Run first-time setup (hooks + deps)"
	@echo "  make check-env                           Check development environment"
	@echo "  make install-hooks                       Install git hooks"
	@echo "  make install-deps                        Install Python dependencies"
	@echo "  make install-gui-deps                    Install GUI (npm) dependencies"
	@echo "  make install-gh                          Install GitHub CLI (macOS/brew)"
	@echo ""
	@echo "Development:"
	@echo "  make dev                                 Start all services via Docker (includes DB + migrations)"
	@echo "  make dev-local                           Start API + GUI locally (requires db-up first)"
	@echo "  make restart                             Stop and restart dev servers"
	@echo "  make dev-stop                            Stop running dev servers"
	@echo ""
	@echo "GUI (Docker):"
	@echo "  make up                                  Start all services (auto-detects GPU)"
	@echo "  make up-gpu                              Force GPU mode"
	@echo "  make up-cpu                              Force CPU-only mode"
	@echo "  make down                                Stop Docker containers"
	@echo "  make api                                 Start API only (local)"
	@echo "  make gui                                 Start GUI only (local)"
	@echo "  make gui-build                           Build GUI for production"
	@echo ""
	@echo "Ollama:"
	@echo "  make ollama-pull MODEL=llama3.2         Pull a model"
	@echo "  make ollama-list                         List available models"
	@echo ""
	@echo "Workflow:"
	@echo "  make workflow STORY=post_03              Run workflow (auto-finds story)"
	@echo "  make workflow STORY=post_03 CONFIG=groq-production   Use named config"
	@echo "  make workflow STORY=post_03 INPUT=x.md   Run with explicit input file"
	@echo "  make workflow-interactive STORY=post_03  Run with content paste prompt"
	@echo "  make workflow-step STEP=draft            Run single workflow step"
	@echo "  make list-configs                        List available workflow configs"
	@echo "  make check-config                        Validate workflow config"
	@echo "  make check-config CONFIG=groq-production Validate named config"
	@echo ""
	@echo "Testing:"
	@echo "  make test                      Run unit tests"
	@echo "  make test-unit                 Run unit tests (verbose)"
	@echo "  make test-int                  Run integration tests"
	@echo "  make test-isolation            Run data isolation tests"
	@echo "  make test-e2e                  Run e2e tests (costs money)"
	@echo "  make coverage                  Generate coverage report"
	@echo "  make test-file FILE=...        Run specific test file"
	@echo "  make ci-report                 Run full CI pipeline with report"
	@echo ""
	@echo "Logging:"
	@echo "  make logs                      List all runs"
	@echo "  make log-states RUN=xxx        Show state log for a run"
	@echo "  make log-tokens RUN=xxx        Show token usage for a run"
	@echo "  make log-summary RUN=xxx       Show run summary"
	@echo ""
	@echo "Evaluation:"
	@echo "  make eval-agents               Agent performance comparison"
	@echo "  make eval-costs                Cost breakdown by agent"
	@echo "  make eval-trend                Quality trend over time"
	@echo "  make eval-post STORY=post_03   Post iteration history"
	@echo "  make eval-summary              Weekly summary"
	@echo ""
	@echo "Personas & Workflows:"
	@echo "  make seed-personas             Update system personas from prompts/"
	@echo "  make sync-workflows            Sync workflow configs to database"
	@echo ""
	@echo "PostgreSQL Database (Phase 0B):"
	@echo "  make db-up                     Start PostgreSQL + PgBouncer"
	@echo "  make db-down                   Stop PostgreSQL + PgBouncer"
	@echo "  make db-migrate                Run Alembic migrations"
	@echo "  make db-rollback               Rollback last migration"
	@echo "  make db-revision MSG=\"...\"     Create new migration"
	@echo "  make db-history                Show migration history"
	@echo "  make db-shell                  Connect to PostgreSQL CLI"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean                     Remove all workflow artifacts"
	@echo ""
	@echo "Git:"
	@echo "  make pr TITLE=\"...\" BODY_FILE=f  Create PR from file (filters self-attribution)"
	@echo "  make pr TITLE=\"...\"              Create PR (opens editor)"

# ============================================================================
# SETUP COMMANDS
# ============================================================================

# First-time setup - run this after cloning the repo
setup: install-hooks install-deps install-gui-deps
	@echo ""
	@echo "=========================================="
	@echo "Setup complete!"
	@echo "=========================================="
	@echo ""
	@echo "Next steps:"
	@echo "  make db-up        # Start PostgreSQL"
	@echo "  make db-migrate   # Run migrations"
	@echo "  make dev          # Start API + GUI"
	@echo ""

# Install git hooks (prevents AI self-attribution in commits)
install-hooks:
	@echo "Installing git hooks..."
	@../hooks/install.sh

# Install Python dependencies
install-deps:
	@echo "Installing Python dependencies..."
	pip install -e ".[dev]" -r requirements-api.txt

# Install GUI dependencies
install-gui-deps:
	@echo "Installing GUI dependencies..."
	cd gui && npm install

# Install GitHub CLI (macOS only, requires Homebrew)
install-gh:
	@echo "Installing GitHub CLI..."
	@command -v brew >/dev/null 2>&1 && brew install gh || echo "Homebrew not found. Install gh manually: https://cli.github.com/"

# Check development environment
check-env:
	@echo "Checking development environment..."
	@echo ""
	@echo "Python:" && python3 --version || echo "  NOT FOUND"
	@echo "Node:" && node --version || echo "  NOT FOUND"
	@echo "npm:" && npm --version || echo "  NOT FOUND"
	@echo "Docker:" && docker --version || echo "  NOT FOUND"
	@echo "gh CLI:" && gh --version 2>/dev/null || echo "  NOT FOUND (run: make install-gh)"
	@echo "Git hooks:" && (test -L "$$(git rev-parse --git-dir)/hooks/pre-commit" && echo "  Installed") || echo "  NOT INSTALLED (run: make install-hooks)"
	@echo ""

# ============================================================================
# WORKFLOW COMMANDS
# ============================================================================

# CONFIG defaults to workflows/configs/claude.yaml
# Can be a name (groq) or path (workflows/configs/groq.yaml)
CONFIG ?= workflows/configs/claude.yaml

workflow:
ifndef STORY
	$(error STORY required. Usage: make workflow STORY=post_03 [CONFIG=groq-production])
endif
ifdef INPUT
	@python3 -m runner.runner --config $(CONFIG) --story $(STORY) --input $(INPUT)
else
	@python3 -m runner.runner --config $(CONFIG) --story $(STORY)
endif

workflow-interactive:
ifndef STORY
	$(error STORY required. Usage: make workflow-interactive STORY=post_03 [CONFIG=groq-production])
endif
	@python3 -m runner.runner --config $(CONFIG) --story $(STORY) --interactive

workflow-step:
ifndef STEP
	$(error STEP required. Usage: make workflow-step STEP=draft STORY=post_03 [CONFIG=groq-production])
endif
ifndef STORY
	$(error STORY required. Usage: make workflow-step STEP=draft STORY=post_03 [CONFIG=groq-production])
endif
	@python3 -m runner.runner --config $(CONFIG) --story $(STORY) --step $(STEP)

list-configs:
	@python3 -m runner.runner --list-configs

check-config:
	@python3 -c "from runner.config import resolve_workflow_config; print(f'Config OK: {resolve_workflow_config(\"$(CONFIG)\")}')"

# ============================================================================
# TEST COMMANDS
# ============================================================================

test: test-unit

test-unit:
	python3 -m pytest tests/unit -v --tb=short

test-int:
	python3 -m pytest tests/integration -v --tb=short

test-isolation:
	python3 -m pytest tests/integration/test_workspace_data_isolation.py tests/integration/test_voice_profiles_isolation.py -v --tb=short

test-e2e:
	python3 -m pytest tests/e2e -v --tb=short -m e2e

coverage:
	python3 -m pytest tests/unit tests/integration \
		--cov=runner \
		--cov-report=html \
		--cov-report=term-missing

test-file:
ifndef FILE
	$(error FILE required. Usage: make test-file FILE=tests/unit/test_circuit_breaker.py)
endif
	python3 -m pytest $(FILE) -v --tb=long

# ============================================================================
# LOG COMMANDS
# ============================================================================

logs:
	@python3 -m runner.runner --config workflows/configs/claude.yaml --list-runs

log-states:
ifndef RUN
	$(error RUN required. Usage: make log-states RUN=2026-01-07_143022_post03)
endif
	@cat workflow/runs/$(RUN)/state_log.jsonl | python3 -m json.tool --no-ensure-ascii 2>/dev/null || \
		echo "No state log found for $(RUN)"

log-tokens:
ifndef RUN
	$(error RUN required. Usage: make log-tokens RUN=2026-01-07_143022_post03)
endif
	@python3 -c "\
import sys, json, os; \
path = 'workflow/runs/$(RUN)/run_manifest.yaml'; \
import yaml; \
data = yaml.safe_load(open(path)) if os.path.exists(path) else {}; \
print(f\"Tokens: {data.get('total_tokens', 0):,}\"); \
print(f\"Cost: \$${data.get('total_cost_usd', 0):.4f}\")" 2>/dev/null || \
	echo "No manifest found for $(RUN)"

log-summary:
ifndef RUN
	$(error RUN required. Usage: make log-summary RUN=2026-01-07_143022_post03)
endif
	@cat workflow/runs/$(RUN)/run_summary.md 2>/dev/null || echo "No summary found for $(RUN)"

# ============================================================================
# MAINTENANCE
# ============================================================================

clean:
	@echo "Removing workflow artifacts..."
	rm -rf workflow/drafts/* workflow/audits/* workflow/final/* workflow/analysis/*
	@echo "Done. Run logs preserved in workflow/runs/"

clean-all:
	@echo "Removing ALL workflow data including runs..."
	rm -rf workflow/drafts/* workflow/audits/* workflow/final/* workflow/analysis/* workflow/runs/*
	@echo "Done."

# ============================================================================
# GUI COMMANDS
# ============================================================================

# Auto-detect GPU support
HAS_GPU := $(shell command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1 && echo 1 || echo 0)
ifeq ($(HAS_GPU),1)
    COMPOSE_FILES := -f docker-compose.yml -f docker-compose.gpu.yml
    GPU_STATUS := (GPU enabled)
else
    COMPOSE_FILES := -f docker-compose.yml
    GPU_STATUS := (CPU only)
endif

up:
	@echo "Starting services... $(GPU_STATUS)"
	docker compose $(COMPOSE_FILES) up --build

down:
	docker compose $(COMPOSE_FILES) down

up-cpu:
	@echo "Starting services... (CPU only, forced)"
	docker compose -f docker-compose.yml up --build

up-gpu:
	@echo "Starting services... (GPU forced)"
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

gui:
	cd gui && npm run dev

watermark:
	cd ../watermark_remover && uvicorn service:app --host 0.0.0.0 --port 8001

# Development mode (Docker) - starts all services in containers
# Includes: postgres, pgbouncer, redis, ollama, api, gui
# Use Ctrl+C to stop
dev:
	@echo "Starting development environment (Docker)... $(GPU_STATUS)"
	@echo "Starting database and running migrations..."
	docker compose $(COMPOSE_FILES) up -d postgres pgbouncer
	@sleep 3
	@docker compose exec postgres pg_isready -U orchestrator || (echo "Waiting for postgres..." && sleep 5)
	cd runner/db/migrations && DATABASE_URL=postgresql://orchestrator:orchestrator_dev@localhost:5434/orchestrator alembic upgrade head
	@echo "Migrations complete. Starting all services..."
	@trap 'docker compose $(COMPOSE_FILES) down' INT TERM; \
	docker compose $(COMPOSE_FILES) up --build

# Development mode (Local) - starts API and GUI on host machine
# Requires: make db-up first for database
dev-local:
	@echo "Starting local development servers..."
	@echo "Note: Database must be running (make db-up)"
	@trap 'kill 0' INT; \
	(uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &); \
	sleep 2; \
	cd gui && npm run dev

# Stop Docker development environment
dev-stop:
	@echo "Stopping development environment..."
	docker compose $(COMPOSE_FILES) down
	@-pkill -f "uvicorn api.main:app" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	@echo "Done."

# Restart development environment
restart: dev-stop dev

gui-build:
	cd gui && npm run build

# ============================================================================
# OLLAMA COMMANDS
# ============================================================================

ollama-pull:
ifndef MODEL
	$(error MODEL required. Usage: make ollama-pull MODEL=llama3.2)
endif
	docker compose exec ollama ollama pull $(MODEL)

ollama-list:
	docker compose exec ollama ollama list

# ============================================================================
# PERSONA COMMANDS
# ============================================================================

# Update system personas from prompts/ directory (refreshes content)
seed-personas:
	@python3 scripts/seed_personas.py

# Seed voice profile presets from prompts/voice_profiles/
seed-voices:
	@python3 scripts/seed_voice_profiles.py

# Sync workflow configs from registry.yaml to database
# DEPLOYMENT_ENV can be: production, development, staging
sync-workflows:
	@python3 scripts/sync_workflows.py

# ============================================================================
# POSTGRESQL DATABASE COMMANDS (Phase 0B - Multi-tenancy)
# ============================================================================

# Start PostgreSQL and PgBouncer
db-up:
	docker compose up -d postgres pgbouncer
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	@docker compose exec postgres pg_isready -U orchestrator
	@echo "PostgreSQL is ready on port 5432 (direct) and 6432 (pooled)"

# Stop PostgreSQL
db-down:
	docker compose stop postgres pgbouncer

# Run Alembic migrations
db-migrate:
	@cd runner/db && alembic upgrade head

# Rollback last migration
db-rollback:
	@cd runner/db && alembic downgrade -1

# Create a new migration
db-revision:
ifndef MSG
	$(error MSG required. Usage: make db-revision MSG="add workspace table")
endif
	@cd runner/db && alembic revision --autogenerate -m "$(MSG)"

# Show migration history
db-history:
	@cd runner/db && alembic history

# Show current migration head
db-current:
	@cd runner/db && alembic current

# Initialize database (development only - use migrations for production)
db-init:
	python3 -c "from runner.db import init_db; init_db()"

# Drop all tables (DANGEROUS - data loss)
db-drop:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && \
		python3 -c "from runner.db.engine import drop_all_tables; drop_all_tables()" || \
		echo "Cancelled."

# Connect to PostgreSQL CLI
db-shell:
	docker compose exec postgres psql -U orchestrator -d orchestrator

# ============================================================================
# GIT COMMANDS
# ============================================================================

# Create PR with self-attribution filtering
# Usage: make pr TITLE="title" BODY_FILE=body.md  (reads from file)
# Usage: make pr TITLE="title"                     (opens editor)
pr:
ifndef TITLE
	$(error TITLE required. Usage: make pr TITLE="My title" BODY_FILE=body.md)
endif
ifdef BODY_FILE
	@bash ./hooks/filter-attribution.sh "$(BODY_FILE)" > /tmp/pr_body_clean.md && \
		gh pr create --title "$(TITLE)" --body-file /tmp/pr_body_clean.md --base main
else
	gh pr create --title "$(TITLE)" --fill --base main
endif
