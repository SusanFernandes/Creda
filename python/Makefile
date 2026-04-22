# ═══════════════════════════════════════════════════════════════════
# CREDA — Makefile  (PowerShell-native)
# Run from: python/ directory  →  make all
#
# NEW USER QUICKSTART:
#   1. make init          (one-time: venv + deps + env + docker + migrate)
#   2. make all           (start everything — backend + frontend + docker)
#   3. Open http://localhost:8000
#
# ═══════════════════════════════════════════════════════════════════

SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

SHELL_EXE := powershell.exe

VENV   := $(CURDIR)/../.venv
PYTHON := $(VENV)/Scripts/python.exe
PIP    := $(VENV)/Scripts/pip.exe

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
	@Write-Host '    make migrate           Run Django + Alembic migrations'
	@Write-Host '    make superuser         Create Django admin superuser'
	@Write-Host '    make seed              Seed demo data (2 users with full data)'
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
init: venv install env docker wait migrate ## One-time full setup
	@Write-Host ''
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host '  Setup complete!' -ForegroundColor Green
	@Write-Host ''
	@Write-Host '  Next steps:'
	@Write-Host '    1. Edit .env and add your GROQ_API_KEY'
	@Write-Host '    2. Run "make all" to start all services'
	@Write-Host '    3. Open http://localhost:8000'
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan

.PHONY: venv
venv: ## Create Python virtual environment
	@if (-not (Test-Path '$(VENV)/Scripts/activate.bat')) { Write-Host 'Creating virtual environment (Python 3.12)...' -ForegroundColor Yellow; python -m venv '$(VENV)'; Write-Host 'Virtual environment created at $(VENV)' -ForegroundColor Green } else { Write-Host 'Virtual environment already exists at $(VENV)' -ForegroundColor Gray }

.PHONY: env
env: ## Create .env from .env.example if missing
	@if (-not (Test-Path '.env')) { if (Test-Path '.env.example') { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example — edit it with your GROQ_API_KEY' -ForegroundColor Yellow } else { Write-Host '.env.example not found — create .env manually.' -ForegroundColor Red } } else { Write-Host '.env already exists — skipping.' -ForegroundColor Gray }

# ─── INSTALL ──────────────────────────────────────────────────────

.PHONY: install
install: install-backend install-frontend ## Install all Python dependencies

.PHONY: install-backend
install-backend: ## Install FastAPI backend dependencies
	@Write-Host 'Installing backend dependencies...' -ForegroundColor Yellow
	@& '$(PIP)' install -r backend/requirements.txt -q
	@Write-Host 'Backend dependencies installed.' -ForegroundColor Green

.PHONY: install-frontend
install-frontend: ## Install Django frontend dependencies
	@Write-Host 'Installing frontend dependencies...' -ForegroundColor Yellow
	@& '$(PIP)' install -r frontend/requirements.txt -q
	@Write-Host 'Frontend dependencies installed.' -ForegroundColor Green

# ─── START SERVICES ───────────────────────────────────────────────

.PHONY: all
all: docker wait backend-bg frontend-bg ## Start everything
	@Write-Host ''
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host '  All services started!' -ForegroundColor Green
	@Write-Host ''
	@Write-Host '  Frontend   : http://localhost:8000'
	@Write-Host '  Backend    : http://localhost:8001'
	@Write-Host '  Backend API: http://localhost:8001/docs'
	@Write-Host '  Postgres   : localhost:8010'
	@Write-Host '  Redis      : localhost:8020'
	@Write-Host '  ChromaDB   : localhost:8030'
	@Write-Host '  Kokoro TTS : localhost:8880'
	@Write-Host '  Piper TTS  : localhost:8890'
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan

.PHONY: docker
docker: ## Start Docker infrastructure services
	docker compose up -d --remove-orphans postgres redis chroma kokoro-tts piper-tts
	@Write-Host 'Docker infrastructure services started.' -ForegroundColor Green

.PHONY: wait
wait:
	@Write-Host 'Waiting for services to be ready...' -ForegroundColor Yellow
	@Start-Sleep -Seconds 12

.PHONY: backend
backend: ## Start FastAPI backend (foreground, port 8001)
	cd backend; & '$(PYTHON)' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

.PHONY: backend-bg
backend-bg: ## Start FastAPI backend (background window)
	@Start-Process $(SHELL_EXE) -ArgumentList '-NoExit', '-Command', "& '$(VENV)/Scripts/Activate.ps1'; Set-Location '$(CURDIR)/backend'; & '$(PYTHON)' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	@Write-Host 'Backend started in new window (port 8001)' -ForegroundColor Green

.PHONY: frontend
frontend: ## Start Django frontend (foreground, port 8000)
	cd frontend; & '$(PYTHON)' -m daphne -b 127.0.0.1 -p 8000 creda.asgi:application

.PHONY: frontend-bg
frontend-bg: ## Start Django frontend (background window)
	@Start-Process $(SHELL_EXE) -ArgumentList '-NoExit', '-Command', "& '$(VENV)/Scripts/Activate.ps1'; Set-Location '$(CURDIR)/frontend'; & '$(PYTHON)' -m daphne -b 127.0.0.1 -p 8000 creda.asgi:application"
	@Write-Host 'Frontend started in new window (port 8000 via daphne ASGI)' -ForegroundColor Green

# ─── STOP / RESTART ───────────────────────────────────────────────

.PHONY: stop
stop: stop-docker stop-backend stop-frontend ## Stop all services
	@Write-Host 'All services stopped.' -ForegroundColor Green

.PHONY: stop-backend
stop-backend: ## Stop backend only
	@Write-Host 'Stopping backend...' -ForegroundColor Yellow
	@Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object { $$_.CommandLine -match 'uvicorn' -and $$_.CommandLine -match '8001' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 1
	@Write-Host 'Backend stopped.' -ForegroundColor Green

.PHONY: stop-frontend
stop-frontend: ## Stop frontend only
	@Write-Host 'Stopping frontend...' -ForegroundColor Yellow
	@Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object { $$_.CommandLine -match 'daphne' -and $$_.CommandLine -match '8000' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 1
	@Write-Host 'Frontend stopped.' -ForegroundColor Green

.PHONY: stop-docker
stop-docker: ## Stop Docker containers
	docker compose down

.PHONY: restart-backend
restart-backend: stop-backend backend-bg ## Restart backend
	@Write-Host 'Backend restarted.' -ForegroundColor Green

.PHONY: restart-frontend
restart-frontend: stop-frontend frontend-bg ## Restart frontend
	@Write-Host 'Frontend restarted.' -ForegroundColor Green

# ─── MIGRATIONS ───────────────────────────────────────────────────

.PHONY: migrate
migrate: migrate-django migrate-alembic ## Run all migrations

.PHONY: migrate-django
migrate-django: ## Run Django migrations
	@Write-Host 'Running Django migrations...' -ForegroundColor Yellow
	cd frontend; & '$(PYTHON)' manage.py makemigrations accounts dashboard
	cd frontend; & '$(PYTHON)' manage.py migrate
	@Write-Host 'Django migrations complete.' -ForegroundColor Green

.PHONY: migrate-alembic
migrate-alembic: ## Run Alembic (FastAPI) migrations
	@Write-Host 'Running Alembic migrations...' -ForegroundColor Yellow
	cd backend; & '$(PYTHON)' -m alembic upgrade head
	@Write-Host 'Alembic migrations complete.' -ForegroundColor Green

.PHONY: superuser
superuser: ## Create Django admin superuser
	cd frontend; & '$(PYTHON)' manage.py createsuperuser

.PHONY: seed
seed: ## Seed demo data (2 users with portfolios, goals, nudges)
	@Write-Host 'Seeding demo data...' -ForegroundColor Yellow
	cd backend; & '$(PYTHON)' seed_demo.py
	@Write-Host 'Demo data seeded.' -ForegroundColor Green

# ─── DATABASE ─────────────────────────────────────────────────────

.PHONY: db-shell
db-shell: ## Open psql shell (creda_api database)
	docker compose exec postgres psql -U creda_admin -d creda_api

.PHONY: db-shell-django
db-shell-django: ## Open psql shell (creda_django database)
	docker compose exec postgres psql -U creda_admin -d creda_django

.PHONY: db-tables
db-tables: ## List all tables in creda_api
	docker compose exec postgres psql -U creda_admin -d creda_api -c '\dt'

.PHONY: db-tables-django
db-tables-django: ## List all tables in creda_django
	docker compose exec postgres psql -U creda_admin -d creda_django -c '\dt'

# ─── TESTING ──────────────────────────────────────────────────────

.PHONY: test
test: test-backend test-frontend ## Quick health check for both services

.PHONY: test-backend
test-backend: ## Check backend health endpoint
	@try { $$r = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -UseBasicParsing -TimeoutSec 5; Write-Host "Backend  OK: $$($$r.StatusCode)" -ForegroundColor Green } catch { Write-Host 'Backend  FAILED — not reachable on :8001' -ForegroundColor Red }

.PHONY: test-frontend
test-frontend: ## Check frontend is reachable
	@try { $$r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/login/' -UseBasicParsing -TimeoutSec 5; Write-Host "Frontend OK: $$($$r.StatusCode)" -ForegroundColor Green } catch { Write-Host 'Frontend FAILED — not reachable on :8000' -ForegroundColor Red }

# ─── UTILS ────────────────────────────────────────────────────────

.PHONY: status
status: ## Show status of all services
	@Write-Host ''
	@Write-Host '  Docker containers:' -ForegroundColor Yellow
	@try { docker compose ps } catch { Write-Host '  (Docker not running)' -ForegroundColor Gray }
	@Write-Host ''
	@Write-Host '  Port 8001 (Backend):' -ForegroundColor Yellow
	@$$b = netstat -aon | Select-String ':8001.*LISTENING'; if ($$b) { $$b | ForEach-Object { Write-Host "    $$_" } } else { Write-Host '    Not running' -ForegroundColor Gray }
	@Write-Host '  Port 8000 (Frontend):' -ForegroundColor Yellow
	@$$f = netstat -aon | Select-String ':8000.*LISTENING'; if ($$f) { $$f | ForEach-Object { Write-Host "    $$_" } } else { Write-Host '    Not running' -ForegroundColor Gray }
	@Write-Host ''

.PHONY: logs
logs: ## Tail Docker logs
	docker compose logs -f

.PHONY: logs-backend
logs-backend: ## Tail backend logs in Docker
	docker compose logs -f backend

.PHONY: clean
clean: ## Remove __pycache__ and .pyc files
	@Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
	@Get-ChildItem -Path . -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
	@Write-Host 'Cleaned.' -ForegroundColor Green

.PHONY: reset
reset: stop clean ## Stop everything + clean

.PHONY: nuke
nuke: ## Stop + wipe ALL data (Postgres, Redis, ChromaDB) + rebuild fresh
	@Write-Host 'NUKING everything — stopping services...' -ForegroundColor Red
	@Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $$_.CommandLine -match 'uvicorn|runserver' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 2
	@Write-Host 'Removing Docker containers + volumes...' -ForegroundColor Yellow
	@docker compose down -v --remove-orphans 2>$$null; $$true
	@Write-Host 'Cleaning pycache...' -ForegroundColor Yellow
	@Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
	@Write-Host 'Starting fresh Docker services...' -ForegroundColor Yellow
	@docker compose up -d postgres redis chroma kokoro-tts piper-tts
	@Write-Host 'Waiting for Postgres to be ready...' -ForegroundColor Yellow
	@$$attempt=0; while ($$attempt -lt 15) { try { docker compose exec -T postgres pg_isready -U creda_admin -d creda_api 2>$$null; if ($$LASTEXITCODE -eq 0) { break }; } catch {}; Start-Sleep -Seconds 2; $$attempt++ }
	@Write-Host 'Running migrations...' -ForegroundColor Yellow
	@& '$(PYTHON)' frontend/manage.py migrate --no-input 2>$$null
	@cd backend; & '$(PYTHON)' -m alembic upgrade head 2>$$null
	@Write-Host ''
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host '  NUKE COMPLETE — All data wiped. Docker running fresh.' -ForegroundColor Green
	@Write-Host '  Run "make all" to start backend + frontend.' -ForegroundColor Cyan
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
