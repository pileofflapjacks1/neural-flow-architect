# Contributing to Neural Flow Architect

Thank you for helping build tools that support agency, flow, and dignity for high-bandwidth BCI users.

## Before you start

1. Read the [README](README.md) and [docs/NOVELTY.md](docs/NOVELTY.md).  
2. Read [docs/privacy/PRIVACY_ETHICS.md](docs/privacy/PRIVACY_ETHICS.md) — privacy is a product requirement.  
3. Skim [docs/architecture/SYSTEM_ARCHITECTURE.md](docs/architecture/SYSTEM_ARCHITECTURE.md).  
4. Agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## What we value

- **User control & transparency** over clever opacity  
- **Local-first** neural processing by default  
- **Adapter boundaries** so BCI sources stay swappable  
- **Accessibility** of both the product UX and the contribution process  
- **Scientific honesty** about what EEG vs intracortical data can support  
- **Small, documented changes** over silent rewrites  

## Development setup

```bash
git clone <your-fork-url>
cd neural-flow-architect
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
mypy src
```

### Pre-commit (recommended)

```bash
pre-commit install
pre-commit run --all-files   # once after install
# pytest also runs on git push (pre-push hook)
```

Optional:

```bash
pip install -e ".[brainflow]"   # hardware / file boards
```

### CI

**Local:**

```bash
./scripts/ci.sh
# or: pre-commit install && pre-commit run --all-files
```

| Gate | Blocking? |
|---|---|
| `ruff check` + `ruff format --check` | Yes |
| `mypy src` (strict) | Yes |
| `pytest` (3.11 + 3.12 on Actions) | Yes |
| `python -m build` | Yes |

**GitHub Actions:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and PR to `main`.

## Project conventions

| Area | Convention |
|---|---|
| Language | Python 3.11+, type hints required on public APIs |
| Style | `ruff` format/lint; line length 100 |
| Packages | Code under `src/neural_flow_architect/` |
| Config | YAML in `configs/` + env vars (`NFA_*`) |
| Logging | `structlog` structured events; never log raw neural samples by default |
| Tests | `pytest`; mark hardware tests `@pytest.mark.integration` |
| Commits | Imperative mood, focused diffs; mention issue numbers when relevant |
| Docs | Update docs when behavior or architecture changes |

### Hard rules

1. **Do not commit real neural data, session recordings from people, or credentials.**  
2. **Do not add cloud neural processing without an explicit, off-by-default consent path.**  
3. **Do not bypass the adapter layer** to hardcode a single headset SDK in core modules.  
4. **Do not implement stimulation / closed-loop write paths** without an architecture review and ethics discussion.  
5. **Agent tools that affect the physical world** must be permission-gated and dry-run capable.  
6. **Medical claims** are forbidden in UI copy and README marketing language.

## Contribution types we love

- Flow science features that stay honest about signal limitations  
- BCI-native UX (dwell targets, low cognitive load, screen reader paths)  
- Privacy, consent, retention, and audit improvements  
- Adapters for new open devices / file formats  
- Tests, fixtures, and evaluation harnesses  
- Documentation, ADRs, and accessibility fixes  
- Personalization that runs offline  

## Pull request process

1. Open an issue for larger features (or comment on an existing one).  
2. Fork and branch from `main` (`feat/…`, `fix/…`, `docs/…`).  
3. Keep PRs focused; include tests for behavioral changes.  
4. Update docs if user-facing or architectural.  
5. Ensure `pytest`, `ruff`, and `mypy` pass.  
6. In the PR description, note privacy impact (if any) and whether adapters/APIs changed.

### PR checklist

- [ ] Tests added/updated  
- [ ] Docs updated  
- [ ] No secrets or neural data  
- [ ] Defaults remain local-first  
- [ ] Overrides / consent considered for new agent actions  

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not open public issues for vulnerabilities involving neural data leakage.

## Roadmap alignment

Large features should map to [docs/roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md). If your idea expands scope (e.g. multi-user cloud training), start with a short design note in `docs/research/` or an ADR.

## Recognition

Contributors are credited in release notes. Significant design contributions may be listed in `NOTICE` or a `CONTRIBUTORS` file as the project matures.

## Questions

Use GitHub Discussions (once enabled) or issues with the `question` label. Implant users who prefer private channels for sensitive UX feedback may request a maintainer contact via SECURITY mail or project maintainers list when published.

Thank you for building carefully.
