#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_ROOT="${OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/agentic-decisionops-workbench}"
BIKE_SHARE_OUTPUT_ROOT="${BIKE_SHARE_OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/bike-share-demand-resilience}"
CONTROL_TOWER_OUTPUT_ROOT="${CONTROL_TOWER_OUTPUT_ROOT:-/DATA/HJ/prj/data-scientist-career/projects/decisionops-control-tower}"
export PYTHONDONTWRITEBYTECODE=1

cd "$PROJECT_ROOT"
mkdir -p "$OUTPUT_ROOT/reports"
python3 -m pytest tests -q --junitxml="$OUTPUT_ROOT/reports/pytest.xml"
PYTHONPATH=src python3 -m agentic_decisionops_workbench.pipeline eval \
  --output-root "$OUTPUT_ROOT" \
  --bike-share-root "$BIKE_SHARE_OUTPUT_ROOT" \
  --control-tower-root "$CONTROL_TOWER_OUTPUT_ROOT"
