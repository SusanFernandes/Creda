#!/bin/bash
# Creates both databases on first PostgreSQL init.
# creda_api   → FastAPI domain tables (Alembic)
# creda_django → Django tables (Django migrations)
set -e
set -u

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE creda_django'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'creda_django')\gexec
    SELECT 'CREATE DATABASE creda_api'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'creda_api')\gexec
    GRANT ALL PRIVILEGES ON DATABASE creda_django TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE creda_api TO $POSTGRES_USER;
EOSQL
