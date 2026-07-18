# Caregiver / Setup Assistant Guide

Help someone get Neural Flow Architect running **once**, then step back.  
Daily control should stay with the BCI user whenever possible.

## Principles

1. **User owns the Pause button** — never hide override controls.  
2. **Do not require the user to share neural data** with you or the cloud.  
3. **Prefer Simple mode** and large targets.  
4. **Document the machine path** (where the project lives) for future updates.

## First-time setup (about 15–20 minutes)

### 1. Install Python 3.11+ and Node (for UI)

Confirm:

```bash
python3 --version   # 3.11+
node --version      # 18+ recommended for frontend
```

### 2. Install the project

```bash
cd /path/to/Projects
git clone https://github.com/pileofflapjacks1/neural-flow-architect.git
cd neural-flow-architect
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

### 3. Optional companion UI

```bash
cd frontend
npm install
cd ..
```

### 4. Launch

```bash
source .venv/bin/activate
nfa doctor          # health check
nfa start --with-ui   # API :8741 + companion UI :5173
```

In another terminal (if using UI):

```bash
cd frontend && npm run dev
```

Open **http://127.0.0.1:5173** (not port 8741) and complete the short onboarding cards.

### 5. Practice without hardware

Use **Start simulator** so the user can learn Pause / Undo / Rest before any implant stream exists.

## What to show the user (2 minutes)

1. **Pause Architect** — biggest safety control  
2. **Undo** — reverse last change  
3. **Rest mode** — when tired  
4. **Presets** — Morning focus vs Wind down  

Leave a sticky note or text file on the desktop:

```text
Neural Flow Architect
Terminal: cd ~/Projects/neural-flow-architect && source .venv/bin/activate && nfa start
UI: http://127.0.0.1:5173
```

## Privacy boundaries for helpers

- Do not email or upload session JSON from `data/sessions/`  
- Do not enable cloud LLM flags  
- Do not commit personal profiles to git  

## When something breaks

```bash
nfa doctor
nfa status
pytest -q
```

If the API port is busy, stop other `nfa serve` processes or change `NFA_API_PORT`.

## Independence check

Setup is done when the user can, without you:

1. Start a session  
2. Pause the Architect  
3. Undo an action  
4. Switch to Rest mode  

That is success.
