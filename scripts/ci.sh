#!/usr/bin/env bash
# Local CI stand-in until GitHub Actions workflow scope is enabled.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -e ".[dev]" -q
python -m ruff check src tests || true
python -m pytest -q
python -m neural_flow_architect.cli contract --adapter simulator
python -m neural_flow_architect.cli doctor
echo "CI stand-in OK"
