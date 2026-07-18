# Implementation status vs core feature map

As of July 2026 (v0.2.x daily-driver foundation).  
This maps the classic “five pillars” product brief to **what already ships** and **recent additions**.

> Research / assistive software — **not a medical device**. Flow scores are proxies.

---

## 1. Flow detection & modeling (`flow/`)

| Capability | Status | Where |
|---|---|---|
| Multi-dimensional proxies (engagement, arousal balance, self-ref, ease) | ✅ | `signal/features.py`, `flow/engine.py` |
| State machine + hysteresis (`pre_flow` → `flow` → `deep_flow` → …) | ✅ | `flow/engine.py` |
| Confidence from signal quality | ✅ | `flow/engine.py`, `signal/quality.py` |
| Simulator / BrainFlow / replay adapters | ✅ | `adapters/` |
| **Hybrid ML calibrator** (sklearn logistic reg on local labels) | ✅ | `flow/ml_calibrator.py` (blend into engine) |
| API: hybrid status | ✅ | `GET /flow/ml` |

Train hybrid ML by tapping **Felt in flow / Not really** during sessions. Needs both classes and ≥8 samples (configurable).

---

## 2. Proactive Architect agent (`agent/`)

| Capability | Status | Where |
|---|---|---|
| Mode selection (protect / re-enter / transition / idle) | ✅ | `agent/policies/modes.py` |
| Multi-module proposals | ✅ | `protector`, `reentry`, `transition` |
| Tool registry + digital/IoT/recipe tools | ✅ | `agent/tools/` |
| Governor (cooldowns, impact caps, never-list) | ✅ | `agent/governor.py` |
| Explainer + optional local LLM wording | ✅ | `explainer.py`, `llm_explainer.py` |
| Undo stack | ✅ | `agent/undo.py` |
| Predictive precursors (opt-in) | ✅ | `agent/predictive.py` |
| Fail-safe integration | ✅ | `core/failsafe.py`, runtime |

Custom lightweight agent (not LangChain) — intentional for latency, offline, and auditability.

---

## 3. Environment orchestration (`environment/`)

| Capability | Status | Where |
|---|---|---|
| Digital density / focus / notify policy | ✅ | `environment/digital.py` |
| OS notifications (best-effort) | ✅ | `os_notifications.py` |
| OS Focus / DND (dry-run default) | ✅ | `os_focus.py` |
| Recipes study/create/rest/social | ✅ | `recipes.py` |
| Home Assistant IoT (soft-fail, dry-run default) | ✅ | `physical.py` |

---

## 4. Personalization (`personalization/`)

| Capability | Status | Where |
|---|---|---|
| Local profile + thresholds JSON | ✅ | `profile.py` |
| Label → threshold learning | ✅ | `learning.py` |
| Block-review learning | ✅ | `learning.py` |
| Feedback affinity (helpful / never) | ✅ | `feedback.py` |
| Personal flow signature v0 | ✅ | `signature.py` |
| Presets + a11y | ✅ | `presets.py`, `a11y.py` |
| Hybrid ML sample store | ✅ | `data/profiles/flow_ml_samples.jsonl` |

---

## 5. Insights & recaps (`insights/`)

| Capability | Status | Where |
|---|---|---|
| Session store + timeline | ✅ | `store.py` |
| Coaching notes | ✅ | `coaching.py` |
| Trust + policy scoreboard + weekly recap | ✅ | `trust.py`, `scoreboard.py` |
| **Post-session helped/hurt recap** | ✅ | `session_recap.py`, `GET /session/recap` |
| Companion Insights UI | ✅ | `frontend/` Insights tab |
| Session recap + Hybrid ML panels | ✅ | `SessionRecapPanel`, `HybridMlPanel` |

---

## Runnable entrypoints

```bash
nfa demo --duration 20
nfa start --with-ui          # UI http://127.0.0.1:5173  API :8741
nfa doctor --brainflow
nfa report --json --days 7
curl -s http://127.0.0.1:8741/flow/ml
curl -s http://127.0.0.1:8741/session/recap
```

---

## Explicit non-goals (still)

- No clinical claims or stimulation / closed-loop write paths  
- No cloud neural processing by default  
- No LangChain dependency for the core agent loop  
