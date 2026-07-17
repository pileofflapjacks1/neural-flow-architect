# User Guide — Neural Flow Architect

**For:** People using (or preparing for) high-bandwidth BCIs, and anyone who wants a calm flow co-pilot.  
**Not a medical device.** Assistive / research software only.

## One-minute start

```bash
cd neural-flow-architect
source .venv/bin/activate   # after first-time install
nfa start
```

Then open **http://127.0.0.1:5173** (companion UI) if you use the frontend,  
or use the API/status output from `nfa start` alone.

First time only:

```bash
pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

## What it does (plain language)

1. Watches **estimated focus / flow-related signals** (simulator today; open EEG or future implant adapter later).  
2. When you seem to enter deep work, it **quietly protects** that state (simpler UI, fewer notices).  
3. You can always **Pause**, **Undo**, or **Rest**.  
4. Optional **labels** (“I felt in flow”) teach it *your* patterns — on this device only.

## Everyday controls (large targets)

| Control | What it does |
|---|---|
| **Start** | Begin a session (simulator or replay — no implant required to practice) |
| **Pause Architect** | Stops proactive actions immediately |
| **Undo** | Reverses the last environment change |
| **Rest mode** | Switches to recovery-friendly settings |
| **I felt in flow / Not really** | Optional self-report for personalization |
| **Preset chips** | Morning focus, Creative, Social, Wind down |

### Simple mode

Default for new users. Shows only the essentials.  
Turn off Simple mode (or pick the **Power user** preset) for predictive toggles, coaching, and advanced tabs.

## If you use a BCI (today or future)

### Today (practice without an implant)

- **Simulator** — synthetic signals for demos  
- **Replay** — fixed synthetic trajectory  
- **BrainFlow** (optional) — open EEG boards  

### Future high-bandwidth path

When a vendor intent API is available, only the **adapter** changes.  
Your controls stay the same. Discrete intents the software understands:

| Intent | Effect |
|---|---|
| `pause_agent` / `resume_agent` | Pause or resume co-pilot |
| `undo` | Undo last action |
| `rest_mode` | Rest recipe + gentle wind-down |
| `label_flow_yes` / `label_flow_no` | Self-report |
| `recipe_study` / `create` / `rest` / `social` | Switch environment recipe |
| `start_session` / `stop_session` | Session control |

See [NEURALINK_READINESS.md](../bci/NEURALINK_READINESS.md).

## Privacy in one glance

- Local-first by default  
- No cloud neural upload  
- Optional local LLM only rewrites **short explanations** from summaries — never raw brain data  
- You can delete session files under `data/sessions/`

## Troubleshooting

| Symptom | Try |
|---|---|
| UI says disconnected | Run `nfa start` or `nfa serve` first |
| Co-pilot too chatty | Pause, or **Never** on a tool in Why? |
| Signal degraded | Architect idles for safety — check hardware/adapter |
| Need a clean check | `nfa doctor` |

## Caregivers

See [CAREGIVER_SETUP.md](CAREGIVER_SETUP.md) for first-time install without taking over daily control.
