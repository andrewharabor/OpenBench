#!/usr/bin/env zsh

set -e

cd "${0:A:h}"

set -a
source .env
set +a

mysql.server start

cleanup() {
  mysql.server stop
}

trap cleanup EXIT INT TERM

uv run --no-project python manage.py runserver 127.0.0.1:8000
