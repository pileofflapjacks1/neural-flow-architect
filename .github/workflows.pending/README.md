# Enable GitHub Actions CI

The workflow file lives here because pushing paths under `.github/workflows/`
requires a GitHub credential with the **`workflow`** scope. The rest of the
quality gates (ruff, pytest, pre-commit, `scripts/ci.sh`) already work without
that scope.

## One-time enable (maintainer)

1. Create or update a [Personal Access Token](https://github.com/settings/tokens)
   with the **`workflow`** scope (classic) or **Actions: write** (fine-grained).
2. From the repo root:

```bash
mkdir -p .github/workflows
mv .github/workflows.pending/ci.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "Enable GitHub Actions CI workflow"
git push origin main
```

3. Confirm the **CI** workflow runs under the repo **Actions** tab.
4. Optional: remove this `workflows.pending/` folder once the live workflow is green.

## Local stand-in (anyone)

```bash
pip install -e ".[dev]"
./scripts/ci.sh
# or
pre-commit install && pre-commit run --all-files
```
