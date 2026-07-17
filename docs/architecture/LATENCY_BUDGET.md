# Latency Budget

Prototype targets for the local closed-loop path. Values are **guidance**, not SLAs.

## Stage budgets (p95)

| Stage | Budget (ms) | Notes |
|---|---|---|
| Feature extract (1s window) | 50 | NumPy FFT path |
| Flow update | 20 | EMA + state machine |
| Agent rules step | 10 | Deterministic policies |
| End-to-end per window | 80 | Feature → decision |
| Optional local LLM wording | async, non-blocking | Never on critical path |
| IoT / OS hooks | async, timeout ≤ 5s | Soft-fail |

## High-channel aspirational

| Channels | Feature budget (ms) | Notes |
|---|---|---|
| 8–64 (open EEG) | 50 | Day-1 path |
| 256–1024 (stub) | 100 | Stress tests; may exceed prototype budget |
| 1000+ | profile + feature-source short-circuit | Phase 3 |

## Measuring

```bash
nfa bench --channels 8 --iterations 40
nfa bench --channels 1024 --iterations 20
```

Reports include mean / p50 / p95 / max per stage and pass/fail vs budgets.

## Principles

1. Control loop must not block on LLM or network IoT.  
2. Under overload, drop oldest frames and degrade quality — do not stall UI.  
3. Document regressions in PR notes when p95 crosses budget.  
