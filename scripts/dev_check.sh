#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m ruff check src tests || true
python -m pytest
python -c "from neural_flow_architect import __version__; print('nfa', __version__)"
