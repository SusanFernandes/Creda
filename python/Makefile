# ═══════════════════════════════════════════════════════════════════
# CREDA — Makefile  (cmd-native, Windows)
# Run from: python/ directory  →  make all
#
# NEW USER QUICKSTART:
#   1. make init          (one-time: venv + deps + env + docker + migrate)
#   2. make all           (start everything — backend + frontend + docker)
#   3. Open http://localhost:8000
#
# ═══════════════════════════════════════════════════════════════════

SHELL := cmd.exe
.SHELLFLAGS := /C

VENV   := $(CURDIR)/../.venv
PYTHON := $(VENV)\Scripts\python.exe
UV     := uv
UV_INDEX_URL := https://pypi.tuna.tsinghua.edu.cn/simple

# ─── HELP ─────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@Write-Host ''
	@Write-Host '  CREDA — AI Financial Coach for India' -ForegroundColor Cyan
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host ''
	@Write-Host '  QUICKSTART' -ForegroundColor Yellow
	@Write-Host '    make init              One-time full setup (venv + deps + env + docker + migrate)'
	@Write-Host '    make all               Start everything (Docker + Backend + Frontend)'
	@Write-Host ''
	@Write-Host '  STARTUP' -ForegroundColor Yellow
	@Write-Host '    make docker            Start Docker services only'
	@Write-Host '    make backend           Start FastAPI backend (port 8001, foreground)'
	@Write-Host '    make backend-bg        Start FastAPI backend (new window)'
	@Write-Host '    make frontend          Start Django frontend (port 8000, foreground)'
	@Write-Host '    make frontend-bg       Start Django frontend (new window)'
	@Write-Host ''
	@Write-Host '  STOP / RESTART' -ForegroundColor Yellow
	@Write-Host '    make stop              Stop all services'
	@Write-Host '    make stop-backend      Stop backend only'
	@Write-Host '    make stop-frontend     Stop frontend only'
	@Write-Host '    make stop-docker       Stop Docker containers only'
	@Write-Host '    make restart-backend   Restart backend'
	@Write-Host '    make restart-frontend  Restart frontend'
	@Write-Host ''
	@Write-Host '  SETUP' -ForegroundColor Yellow
	@Write-Host '    make venv              Create Python virtual environment'
	@Write-Host '    make install           Install all Python dependencies'
	@Write-Host '    make env               Create .env from .env.example'
	@Write-Host '    make download-model    Download MiniLM to local models/ (offline embeddings)'
	@Write-Host '    make postgres-volume-reset  Fix DB password mismatch (removes Postgres volume; wipes DB)'
	@Write-Host '    make migrate           Run Django + Alembic migrations'
	@Write-Host '    make superuser         Create Django admin superuser'
	@Write-Host '    make seed              Seed demo data (Arjun + Priya with full portfolio)'
	@Write-Host ''
	@Write-Host '  DATABASE' -ForegroundColor Yellow
	@Write-Host '    make db-shell          Open psql shell (creda_api)'
	@Write-Host '    make db-shell-django   Open psql shell (creda_django)'
	@Write-Host '    make db-tables         List all tables in creda_api'
	@Write-Host ''
	@Write-Host '  TESTING' -ForegroundColor Yellow
	@Write-Host '    make test              Quick health check (backend + frontend)'
	@Write-Host '    make test-backend      Backend health endpoint'
	@Write-Host ''
	@Write-Host '  UTILS' -ForegroundColor Yellow
	@Write-Host '    make status            Show status of all services'
	@Write-Host '    make logs              Tail Docker logs'
	@Write-Host '    make clean             Remove __pycache__ and .pyc files'
	@Write-Host '    make reset             Stop everything + clean'
	@Write-Host '    make nuke              Stop + wipe ALL data + rebuild fresh'
	@Write-Host ''

# ─── FIRST-TIME INIT ─────────────────────────────────────────────

.PHONY: init
init: venv install env download-model docker wait db-init migrate
	@echo.
	@echo   ═══════════════════════════════════════════════════
	@echo   Setup complete!
	@echo.
	@echo   Next steps:
	@echo     1. Edit .env and add your GROQ_API_KEY
	@echo     2. Run "make all" to start all services
	@echo     3. Open http://localhost:8000
	@echo     Note: MiniLM model (~87MB) was downloaded to models/ for offline intent matching.
	@echo   ═══════════════════════════════════════════════════

.PHONY: download-model
download-model:
	@echo Downloading sentence-transformers/all-MiniLM-L6-v2 (~87MB)...
	"$(PYTHON)" -c "from sentence_transformers import SentenceTransformer; from pathlib import Path; d=Path('models/all-MiniLM-L6-v2'); m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); d.parent.mkdir(parents=True,exist_ok=True); m.save(str(d)); print('Saved to',d)"
	@echo Model downloaded and saved locally.

.PHONY: venv
venv:
	@if not exist "$(VENV)\Scripts\activate.bat" ( echo Creating virtual environment... && python -m venv "$(VENV)" && echo Done. ) else ( echo Virtual environment already exists. )

.PHONY: env
env: ## Create .env from .env.example if missing
	@if (-not (Test-Path '.env')) { if (Test-Path '.env.example') { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example — edit it with your GROQ_API_KEY' -ForegroundColor Yellow } else { Write-Host '.env.example not found — create .env manually.' -ForegroundColor Red } } else { Write-Host '.env already exists — skipping.' -ForegroundColor Gray }

.PHONY: postgres-volume-reset
postgres-volume-reset: ## Remove Postgres volume and recreate container (fixes stale password; destroys DB data)
	@Write-Host 'Removing Postgres container and volume (all Postgres data for this compose project)...' -ForegroundColor Yellow
	docker compose stop postgres
	docker compose rm -f postgres
	@$$proj = Split-Path '$(CURDIR)' -Leaf; $$vol = $$proj + '_postgres_data'; docker volume rm $$vol 2>$$null; if ($$LASTEXITCODE -ne 0) { Write-Host ('Note: could not remove volume ' + $$vol + ' (missing or in use). Try: docker volume ls') -ForegroundColor Gray }
	docker compose up -d postgres
	@Write-Host 'Postgres is starting. Wait ~10s, then run: make migrate' -ForegroundColor Green

# ─── INSTALL ──────────────────────────────────────────────────────

.PHONY: install
install: install-backend install-frontend

.PHONY: install-backend
install-backend:
	@echo Installing backend dependencies...
	$(UV) pip install --python "$(PYTHON)" -r backend/requirements.txt -i $(UV_INDEX_URL)
	@echo Backend dependencies installed.

.PHONY: install-frontend
install-frontend:
	@echo Installing frontend dependencies...
	$(UV) pip install --python "$(PYTHON)" -r frontend/requirements.txt -i $(UV_INDEX_URL)
	@echo Frontend dependencies installed.

# ─── START SERVICES ───────────────────────────────────────────────

.PHONY: all
all: docker wait backend-bg frontend-bg
	@echo.
	@echo   ═══════════════════════════════════════════════════
	@echo   All services started!
	@echo.
	@echo   Frontend   : http://localhost:8000
	@echo   Backend    : http://localhost:8001
	@echo   Backend API: http://localhost:8001/docs
	@echo   Postgres   : localhost:8010
	@echo   Redis      : localhost:8020
	@echo   ChromaDB   : localhost:8030
	@echo   Piper TTS  : localhost:8890
	@echo   ═══════════════════════════════════════════════════

.PHONY: docker
docker:
	docker compose up -d --remove-orphans postgres redis chroma piper-tts
	@echo Docker infrastructure services started.

.PHONY: wait
wait:
	@echo Waiting for Postgres to be ready...
	:retry
	docker compose exec postgres pg_isready -U creda_admin -d creda_api >nul 2>&1 || (timeout /t 3 /nobreak >nul && goto retry)
	@echo Postgres is ready.

.PHONY: db-init
db-init:
	@echo Creating databases if not exists...
	-docker compose exec postgres psql -U creda_admin -d postgres -c "CREATE DATABASE creda_django OWNER creda_admin;"
	@echo Databases ready.

.PHONY: backend
backend:
	cd backend && "$(PYTHON)" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

.PHONY: backend-bg
backend-bg:
	start "CREDA Backend" cmd /k "cd /d $(CURDIR)\backend && "$(PYTHON)" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	@echo Backend started in new window (port 8001)

.PHONY: frontend
frontend:
	cd frontend && "$(PYTHON)" -m daphne -b 127.0.0.1 -p 8000 creda.asgi:application

.PHONY: frontend-bg
frontend-bg:
	start "CREDA Frontend" cmd /k "cd /d $(CURDIR)\frontend && "$(PYTHON)" -m daphne -b 127.0.0.1 -p 8000 creda.asgi:application"
	@echo Frontend started in new window (port 8000)

# ─── STOP / RESTART ───────────────────────────────────────────────

.PHONY: stop
stop: stop-backend stop-frontend stop-docker
	@echo All services stopped.

.PHONY: stop-backend
stop-backend:
	@echo Stopping backend...
	-taskkill /F /FI "WINDOWTITLE eq CREDA Backend*" >nul 2>&1
	@echo Backend stopped.

.PHONY: stop-frontend
stop-frontend:
	@echo Stopping frontend...
	-taskkill /F /FI "WINDOWTITLE eq CREDA Frontend*" >nul 2>&1
	@echo Frontend stopped.

.PHONY: stop-docker
stop-docker:
	docker compose down

.PHONY: restart-backend
restart-backend: stop-backend backend-bg
	@echo Backend restarted.

.PHONY: restart-frontend
restart-frontend: stop-frontend frontend-bg
	@echo Frontend restarted.

# ─── MIGRATIONS ───────────────────────────────────────────────────

.PHONY: migrate
migrate: migrate-django migrate-alembic

.PHONY: migrate-django
migrate-django:
	@echo Running Django migrations...
	cd frontend && "$(PYTHON)" manage.py makemigrations accounts dashboard
	cd frontend && "$(PYTHON)" manage.py migrate
	@echo Django migrations complete.

.PHONY: migrate-alembic
migrate-alembic:
	@echo Running Alembic migrations...
	cd backend && "$(PYTHON)" -m alembic upgrade head
	@echo Alembic migrations complete.

.PHONY: superuser
superuser:
	cd frontend && "$(PYTHON)" manage.py createsuperuser

.PHONY: seed
seed:
	@echo Seeding demo data...
	cd backend && "$(PYTHON)" seed_demo.py
	@echo Demo data seeded.

# ─── DATABASE ─────────────────────────────────────────────────────

.PHONY: db-shell
db-shell:
	docker compose exec postgres psql -U creda_admin -d creda_api

.PHONY: db-shell-django
db-shell-django:
	docker compose exec postgres psql -U creda_admin -d creda_django

.PHONY: db-tables
db-tables:
	docker compose exec postgres psql -U creda_admin -d creda_api -c "\dt"

.PHONY: db-tables-django
db-tables-django:
	docker compose exec postgres psql -U creda_admin -d creda_django -c "\dt"

# ─── TESTING ──────────────────────────────────────────────────────

.PHONY: test
test: test-backend test-frontend

.PHONY: test-backend
test-backend:
	@curl -s -o nul -w "Backend  OK: %%{http_code}\n" http://127.0.0.1:8001/health || echo Backend FAILED - not reachable on :8001

.PHONY: test-frontend
test-frontend:
	@curl -s -o nul -w "Frontend OK: %%{http_code}\n" http://127.0.0.1:8000/login/ || echo Frontend FAILED - not reachable on :8000

# ─── UTILS ────────────────────────────────────────────────────────

.PHONY: status
status:
	@echo.
	@echo   Docker containers:
	@docker compose ps
	@echo.
	@echo   Port 8001 (Backend):
	@netstat -aon | findstr ":8001" | findstr "LISTENING" || echo     Not running
	@echo   Port 8000 (Frontend):
	@netstat -aon | findstr ":8000" | findstr "LISTENING" || echo     Not running
	@echo.

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: logs-backend
logs-backend:
	docker compose logs -f backend

.PHONY: clean
clean:
	@echo Cleaning pycache...
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	del /s /q *.pyc >nul 2>&1
	@echo Cleaned.

.PHONY: reset
reset: stop clean

.PHONY: nuke
nuke: stop
	@echo NUKING everything - wiping all data...
	docker compose down -v --remove-orphans
	@echo Cleaning pycache...
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	@echo Starting fresh Docker services...
	docker compose up -d postgres redis chroma piper-tts
	@echo Waiting for Postgres to be ready...
	timeout /t 15 /nobreak >nul
	@echo Running migrations...
	cd frontend && "$(PYTHON)" manage.py migrate --no-input
	cd backend && "$(PYTHON)" -m alembic upgrade head
	@echo.
	@echo   ═══════════════════════════════════════════════════
	@echo   NUKE COMPLETE - All data wiped. Docker running fresh.
	@echo   Run "make all" to start backend + frontend.
	@echo   ═══════════════════════════════════════════════════