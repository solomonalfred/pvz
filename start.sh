#!/usr/bin/env bash
set -e

alembic upgrade head

python source/grpc_server.py &

uvicorn source.app:app --host 0.0.0.0 --port ${PORT}
