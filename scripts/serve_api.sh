#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/agentic-decisionops-workbench}"
BIKE_SHARE_OUTPUT_ROOT="${BIKE_SHARE_OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/bike-share-demand-resilience}"
CONTROL_TOWER_OUTPUT_ROOT="${CONTROL_TOWER_OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/decisionops-control-tower}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8092}"

export OUTPUT_ROOT
export BIKE_SHARE_OUTPUT_ROOT
export CONTROL_TOWER_OUTPUT_ROOT
export PYTHONDONTWRITEBYTECODE=1

cd "$PROJECT_ROOT"
PYTHONPATH=src uvicorn agentic_decisionops_workbench.app:app --host "$HOST" --port "$PORT"
