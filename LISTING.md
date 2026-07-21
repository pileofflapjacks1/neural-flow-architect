# NeuraBeach listing — Neural Flow Architect

**Source of truth for catalog re-seed** (storefront: [NeuraBeach](https://neurabeach.vercel.app)).  
Package metadata machine form: [`neurabeach-manifest.json`](./neurabeach-manifest.json).

| Field | Value |
|-------|--------|
| **slug** | `neural-flow-architect` |
| **title** | Neural Flow Architect |
| **version** | `0.2.0` |
| **category** | `research_utility` |
| **featured** | yes |
| **collection** | `col-neura-suite` |
| **suite_role** | `research` |
| **license** | Apache-2.0 (`apache-2.0`) |
| **GitHub** | https://github.com/pileofflapjacks1/neural-flow-architect |
| **Live listing** | https://neurabeach.vercel.app/projects/neural-flow-architect |
| **Suite** | https://neurabeach.vercel.app/collections/col-neura-suite |
| **Live demo URL** | *none* (`null`) — research CLI, not a hosted product |
| **safety_class** | `research_only` |
| **runtime** | `cli` |
| **min_python** | `3.11` |
| **banned_claims** | `true` |
| **depends_on** | `[]` (does not require NeuralBridge at runtime) |

---

## Short description (catalog card)

Closed-loop **research** co-pilot for flow-related engagement on high-bandwidth BCI computer paths: local signal adapters (simulator / optional BrainFlow), multi-dimensional flow proxies, proactive Architect agent, environment hooks, and personalization. **Not a medical device. Not implant firmware. Not the NeuraBinder live demo.**

---

## Suite role (do not conflate)

| Piece | Role |
|-------|------|
| **NeuraBeach** | Catalog / store — where you find computer-side BCI tools |
| **NeuraBinder** | End-user app + live demo |
| **NeuralBridge** | Intent middleware (library) |
| **Intent → OS** | Reference OS adapter |
| **Neural Flow Architect (this)** | **Research** flow co-pilot (`suite_role: research`) |

North star: *NeuraBeach is where you find tools; NeuraBinder is the live demo; NeuralBridge is how apps share intents.*  
NFA is the **research** layer — architecture-ready for high-bandwidth streams, usable today with open tools and simulators.

---

## Screenshots (public raw URLs — must HTTP 200)

Base:  
`https://raw.githubusercontent.com/pileofflapjacks1/neural-flow-architect/main/docs/assets/demo/`

| Asset | URL |
|-------|-----|
| Hero | …/demo-hero.png |
| Frame 1 | …/demo-frame-1.png |
| Frame 2 | …/demo-frame-2.png |
| Frame 3 | …/demo-frame-3.png |
| Frame 4 (optional) | …/demo-frame-4.png |
| Animated walkthrough (optional) | …/nfa-companion-demo.gif |

Full absolute URLs for Beach seed:

```
https://raw.githubusercontent.com/pileofflapjacks1/neural-flow-architect/main/docs/assets/demo/demo-hero.png
https://raw.githubusercontent.com/pileofflapjacks1/neural-flow-architect/main/docs/assets/demo/demo-frame-1.png
https://raw.githubusercontent.com/pileofflapjacks1/neural-flow-architect/main/docs/assets/demo/demo-frame-2.png
https://raw.githubusercontent.com/pileofflapjacks1/neural-flow-architect/main/docs/assets/demo/demo-frame-3.png
```

Stills are **product mockups** of the companion UI concept for onboarding/marketing — not clinical imagery. Captions should say research software.

---

## Safety blurb (required on listing)

> **Research software only.** Neural Flow Architect is not intended to diagnose, treat, cure, or prevent any disease. It is not a regulated medical device (SaMD), not implant firmware, and not affiliated with Neuralink Corp. Neural data defaults to **local** processing. The user remains in control (Pause / Undo / consent). No hosted “Live demo” product URL — run the open-source CLI (and optional local UI) yourself.

---

## Tags

`neura-suite` · `neural-flow-architect` · `bci` · `research` · `flow` · `local-first` · `privacy` · `apache-2.0` · `cli` · `research_utility` · `brainflow-optional`

---

## Install (catalog block)

Requirements: **Python 3.11+**, macOS / Linux / Windows. Node optional (companion UI only).

```bash
git clone https://github.com/pileofflapjacks1/neural-flow-architect.git
cd neural-flow-architect
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m neural_flow_architect --help
# or: nfa --help

nfa doctor
nfa demo --duration 20
nfa start --with-ui
# Companion UI: http://127.0.0.1:5173
# API only:     http://127.0.0.1:8741/health
```

Optional open EEG:

```bash
pip install -e ".[brainflow]"
nfa doctor --brainflow
```

---

## Compatibility

| Item | Support |
|------|---------|
| Python | 3.11+ |
| Adapters | simulator (default), replay, BrainFlow file/synthetic/live (optional), neuralink_stub (intent practice only) |
| Privacy | Local-first; no cloud neural by default |
| UI | Optional Vite companion (`frontend/`) — **local**, not a Vercel product URL |

---

## Manifest entrypoint

```text
python -m neural_flow_architect --help
```

Also installed console script: `nfa`.

---

## Beach re-seed notes

When re-seeding from this repo into NeuraBeach:

1. Prefer **this file + `neurabeach-manifest.json`** over hand-edited Beach seed drift.  
2. Keep `demo_video_url` / live demo CTA **null**.  
3. Keep `suite_role: research` and collection `col-neura-suite`.  
4. Screenshots: raw.githubusercontent.com paths above (verified public).  
5. Do not mark NFA as depending on NeuralBridge for install.
