#!/usr/bin/env zsh

cd "${0:A:h}"

set -a
source .env
set +a

mysql.server start
