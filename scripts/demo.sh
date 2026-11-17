#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
DEMO_ID="$(date -u +%Y%m%dT%H%M%S)-$$"
DEMO_RUNS="runs/demo-$DEMO_ID"
DEMO_REPORT="reports/demo-$DEMO_ID"
.venv/bin/python -m handoverai simulate --config configs/blocked_corridor.yaml --output "$DEMO_RUNS"
.venv/bin/python -m handoverai report --runs "$DEMO_RUNS" --output "$DEMO_REPORT"
printf '\nOpen %s/index.html in your browser.\n' "$DEMO_REPORT"
if [ "$(uname)" = Darwin ]; then open "$DEMO_REPORT/index.html"; fi
