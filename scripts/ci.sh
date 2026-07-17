#!/usr/bin/env bash
# Local mirror of GitHub Actions CI (.github/workflows/ci.yml).
# Usage: ./scripts/ci.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> ruff check"
ruff check src tests

echo "==> ruff format --check"
ruff format --check src tests

echo "==> mypy"
mypy src

echo "==> pytest"
pytest -q --tb=short

echo "==> build"
python -m build

echo "OK — local CI passed"
