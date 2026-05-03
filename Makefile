# Alluci Sovereign Agent v6.4 — Orchestration

VENV = .venv
PYTHON = $(VENV)/bin/python3
UVICORN = $(VENV)/bin/uvicorn

.PHONY: start stop restart status init doctor logs clean quality

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
	@echo "Stopping all processes..."
	@pkill -9 -f uvicorn || true
	@pkill -9 -f vite || true
	@pkill -9 -f node || true
	@sleep 1

start: stop
	@echo "Starting Alluci Sovereign Agent..."
	@nohup $(PYTHON) -m uvicorn backend.app:app --port 8000 --host 0.0.0.0 > backend.log 2>&1 &
	@nohup npm run dev -- --port 3000 --host 0.0.0.0 > frontend.log 2>&1 &
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
