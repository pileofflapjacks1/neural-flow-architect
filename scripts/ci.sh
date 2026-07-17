#!/usr/bin/env bash
# Local mirror of GitHub Actions CI (.github/workflows/ci.yml).
# Usage: ./scripts/ci.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> ruff check"
ruff check src tests

echo "==> ruff format --check"
ruff format --check src tests

echo "==> pytest"
pytest -q --tb=short

echo "==> mypy (advisory)"
mypy src || echo "mypy reported issues (non-blocking in CI)"

echo "==> build"
python -m build

echo "OK — local CI passed (mypy may warn)"
