# Alluci Sovereign Agent v6.4 — Orchestration

VENV = .venv
PYTHON = $(VENV)/bin/python3
UVICORN = $(VENV)/bin/uvicorn
NPM := $(shell which npm 2>/dev/null || echo npm)
NPX := $(shell which npx 2>/dev/null || echo npx)

.PHONY: start stop restart status init doctor logs clean quality docs

help:
	@echo "Alluci Sovereign Agent — Automation"
	@echo "  make init      - Initialize .env and virtual environment"
	@echo "  make start     - Cleanly start Backend (8000) and Frontend (3000)"
	@echo "  make stop      - Force kill all node/uvicorn/vite processes"
	@echo "  make restart   - stop + start"
	@echo "  make status    - Check port 8000/3000 status"
	@echo "  make doctor    - Validate environment, secrets, and dependencies"
	@echo "  make quality   - Run full quality suite (tests, types, lint)"
	@echo "  make logs      - Stream combined logs"

init:
	@echo "Initializing Alluci environment..."
	@./scripts/bootstrap_all.sh

stop:
	@echo "Stopping all processes gracefully..."
	@lsof -ti :8000 | xargs kill -15 2>/dev/null || true
	@lsof -ti :3000 | xargs kill -15 2>/dev/null || true
	@sleep 1

start: stop
	@echo "Starting Alluci Sovereign Agent..."
	@nohup $(PYTHON) -m uvicorn backend.app:app --port 8000 --host 0.0.0.0 > backend.log 2>&1 &
	@nohup $(NPM) run dev -- --port 3000 --host 0.0.0.0 > frontend.log 2>&1 &
	@echo "Backend starting on http://localhost:8000"
	@echo "Frontend starting on http://localhost:3000"
	@echo "Use 'make logs' to watch progress."

restart: start

status:
	@echo "--- Ports ---"
	@lsof -i :8000 || echo "Port 8000 is FREE"
	@lsof -i :3000 || echo "Port 3000 is FREE"

doctor:
	@echo "--- Alluci Doctor ---"
	@$(PYTHON) scripts/verify_local.py

preflight:
	@./scripts/production_readiness/preflight.sh

quality: preflight
	@echo "--- Running Production Quality Gate ---"
	@./scripts/production_readiness/generate_release_report.py
	@echo "--- Quality Gate PASSED ---"

logs:
	@tail -f backend.log frontend.log

docs:
	@echo "Extracting OpenAPI schema..."
	@$(PYTHON) scripts/export_openapi.py
	@echo "Generating Markdown API Reference..."
	@$(NPX) widdershins --search false --language_tabs "python:Python" "javascript:JavaScript" --summary Documentation/openapi.json -o Documentation/API_Reference.md
	@echo "API Reference generated at Documentation/API_Reference.md"
