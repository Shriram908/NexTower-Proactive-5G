#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"'
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
printf '\nInstalled. Next: source .venv/bin/activate && python -m pytest -q\n'
