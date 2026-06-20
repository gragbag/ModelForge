#!/bin/bash
# Runs once when the Postgres data volume is first initialized. Creates a
# SEPARATE `mlflow` database so MLflow's tables live apart from the app's
# tables (otherwise Alembic autogenerate would try to drop MLflow's tables).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE mlflow;
EOSQL
