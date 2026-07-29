# AGENTS.md — Neural Flow Architect (NFA)

You are working on **Neural Flow Architect only** unless the user asks to edit another suite repo.

## Product

**Research** flow-state co-pilot for high-bandwidth BCI computer use: local signal adapters, multi-dimensional flow proxies, proactive Architect agent, environment hooks, personalization.

- **Version:** 0.2.0 (see `pyproject.toml` / manifest)
- **Suite role:** `research` — not Binder’s product demo, not Shell control plane
- Local-first CLI + optional hosted **synthetic** browser demo
- **Not** a medical device (SaMD) · **not** implant firmware · **not** Neuralink-affiliated

## Boundaries

- Privacy / consent / Pause / Undo are product requirements — see `docs/privacy/`.
- Do not claim clinical efficacy or live neural streaming in the hosted demo (synthetic engagement only).
- Do not merge into Neura monorepos or add implant SDKs without explicit ask.
- On listing/version changes: update `LISTING.md` + `neurabeach-manifest.json`.

## Layout

```
src/neural_flow_architect/   Python package (CLI: nfa)
frontend/                    Vite companion / demo UI
configs/ examples/ tests/ docs/
LISTING.md
neurabeach-manifest.json
TODO.md
```

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
nfa --help

# Hosted-style demo UI
cd frontend && npm install
npm run dev:demo          # or build:demo / preview per package.json
```

Prefer project `.venv` over system/Anaconda Python.

## Commits

Author: Joe \<pileofflapjacks1@gmail.com\>  
Repo: https://github.com/pileofflapjacks1/neural-flow-architect  
Demo: https://neural-flow-architect.vercel.app  
License: Apache-2.0

## Related suite (do not edit unless asked)

NeuraBeach · NeuraShell · NeuraBinder · Neurabridge · NeuraRoboBridge
