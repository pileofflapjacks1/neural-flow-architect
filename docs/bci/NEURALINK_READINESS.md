# Neuralink / High-Bandwidth Readiness

This project is **independent** and not affiliated with Neuralink Corp.  
It is designed so a future high-bandwidth intent/feature API can plug in **without rewriting** flow detection, the Architect, or the companion UI.

## Design promise

```text
Vendor SDK / Intent API  →  BCIAdapter (only layer that changes)
                              ↓
                         NeuralFrame / IntentEvent
                              ↓
                    Flow engine + Architect + UI (stable)
```

## What works today for practice

| Path | Purpose |
|---|---|
| `simulator` | Daily UI/agent practice |
| `replay` | Deterministic demos & CI |
| `neuralink_stub` | High-channel + intent stream rehearsal |
| `brainflow` | Open EEG experiments |

```bash
nfa serve --adapter neuralink_stub
# Intent events (pause, etc.) are consumed by the IntentRouter when confidence is high enough
```

## Intent vocabulary (stable)

Adapters should emit `IntentEvent` with these `intent_type` values when available:

| intent_type | Co-pilot action |
|---|---|
| `pause_agent` | Pause proactive Architect |
| `resume_agent` | Resume |
| `undo` | Undo last reversible action |
| `rest_mode` | Rest recipe / wind-down |
| `label_flow_yes` / `label_flow_no` | Self-report personalization |
| `recipe_study` / `recipe_create` / `recipe_rest` / `recipe_social` | Environment recipe |
| `start_session` / `stop_session` | Session lifecycle |
| `why` / `help` | UI hint only |

Minimum confidence default: **0.5** (configurable). Low-confidence intents are ignored — safer for noisy decoders.

## Feature streams vs raw samples

Prefer vendor **feature** or **intent** streams over raw voltage when possible:

- Smaller privacy surface  
- Lower bandwidth  
- Clearer consent story  

If raw frames are available, they still enter only via `NeuralFrame` and default to **no disk persistence**.

## Building a real vendor adapter

1. Copy `adapters/neuralink_stub.py` → `adapters/vendor_name.py`  
2. Implement `BCIAdapter` (`connect`, `stream`, optional `intents`)  
3. Register in `adapters/registry.py`  
4. Map vendor channel layouts honestly in `StreamMetadata`  
5. Never log raw samples at info level  
6. Add contract tests under `tests/unit/`  

See [ADAPTER_LAYER.md](ADAPTER_LAYER.md).

## Accessibility of control

Implant users often rely on **dwell / low-precision** pointing or discrete neural clicks:

- Companion UI uses large targets (≥64px)  
- Intent channel allows control **without** fine cursor use  
- Simple mode hides advanced clutter  

## Safety for daily use

- Pause always available  
- Degraded signal → Architect idles  
- Physical IoT off by default  
- Not a medical device; no stimulation control in this phase  

## Open work before “production implant daily driver”

- [ ] Licensed integration with a real high-level API  
- [ ] Clinical/research partner validation (no PHI in public git)  
- [ ] User studies on dwell timing and explanation trust  
- [ ] Optional OS Focus Mode deep links per platform  

Until then, **simulator + intent stub** remain the honest path to build habits and software quality.
