# Day-1 Prototyping Plan

**Objective:** Within one working session, run a **closed loop** on a developer machine:

```text
simulated neural frames → features → flow state → Architect decision → explanation
```

No implant and no EEG headset required for Day 1.

---

## Prerequisites

| Item | Notes |
|---|---|
| Python 3.11+ | `python3 --version` |
| Git | clone this repo |
| Terminal | macOS / Linux / Windows |
| Optional | BrainFlow-compatible board for Day 1+ hardware path |

---

## Hour-by-hour plan

### Hour 0:00–0:20 — Install

```bash
cd /Users/joe/Projects/neural-flow-architect
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Expected: tests pass; package importable.

### Hour 0:20–0:40 — Run simulator demo

```bash
nfa demo --duration 30
# or
python -m neural_flow_architect.cli demo --duration 30
```

Expected console output:

- Live flow state transitions  
- Architect actions (e.g. focus enable, notification suppress)  
- Human-readable explanations  

Optional script:

```bash
python prototypes/day1/run_closed_loop.py
```

### Hour 0:40–1:10 — Read the vertical slice in code

Read in order:

1. `src/neural_flow_architect/adapters/simulator.py`  
2. `src/neural_flow_architect/signal/features.py`  
3. `src/neural_flow_architect/flow/engine.py`  
4. `src/neural_flow_architect/agent/architect.py`  
5. `src/neural_flow_architect/core/runtime.py`  

Sketch on paper: where you would plug BrainFlow.

### Hour 1:10–1:40 — Config & privacy defaults

```bash
cp .env.example .env
nfa status
```

Verify:

- Local-only defaults  
- IoT disabled  
- Adapter = simulator  

### Hour 1:40–2:30 — First contribution-sized experiment

Pick one:

1. Tweak flow thresholds in `configs/default.yaml` and observe demo behavior  
2. Add a new low-impact tool (e.g. `ui.show_status` variant)  
3. Add a unit test for a protect-mode policy case  
4. Improve Rich console layout for dwell-friendly readability  

### Optional Hour 2:30+ — BrainFlow path

```bash
pip install -e ".[brainflow]"
# Configure board id / port in .env
nfa stream --adapter brainflow
```

If no hardware: use BrainFlow synthetic board if available, or stay on simulator.

---

## Libraries used on Day 1

| Library | Role |
|---|---|
| `numpy`, `scipy` | Signal features |
| `pydantic` | Event schemas |
| `typer`, `rich` | CLI UX |
| `scikit-learn` | Optional simple models later |
| `pytest` | Tests |
| `brainflow` (optional) | Hardware / synthetic boards |

**Not required Day 1:** torch, cloud APIs, Home Assistant, frontend build.

---

## Definition of done (Day 1)

- [ ] `pip install -e ".[dev]"` works  
- [ ] `pytest` green  
- [ ] `nfa demo` shows state changes + explanations  
- [ ] You can point to the adapter interface you would implement next  
- [ ] You did not need to commit any neural data  

---

## Day 2–3 suggested follow-ons

1. BrainFlow file replay fixture  
2. WebSocket state publish  
3. Minimal companion UI flow ring  
4. Preference store for undo  

See [ROADMAP.md](ROADMAP.md) Phase 1.
