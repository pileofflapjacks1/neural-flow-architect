# Threat Model (STRIDE-lite) — Neural Flow Architect

**Scope:** Local single-user install. Public open-source software.  
**Asset:** Neural signals, derived features, preferences, session summaries.

## Assets

| Asset | Sensitivity | Default location |
|---|---|---|
| Raw neural frames | Critical biometric | RAM only (ring buffer) |
| Derived features / flow estimates | High | Optional short local sessions |
| Preferences / feedback / denied tools | Medium | `data/profiles/` |
| Session summaries | Medium | `data/sessions/` |
| IoT tokens | High | env / local only, never git |
| Explanations / audit | Low–Medium | in-memory + optional session JSON |

## Trust boundaries

```text
[ BCI hardware / SDK ] --adapter--> [ NFA core (localhost) ] --ws/rest--> [ Companion UI ]
                                      |
                                      +--> optional IoT (dry-run default)
                                      +--> optional local LLM (summaries only)
```

Nothing leaves the machine unless the user explicitly enables a non-default path.

## STRIDE summary

| Threat | Example | Mitigation |
|---|---|---|
| **S**poofing | Fake local client | Bind API to `127.0.0.1`; no auth on LAN by design |
| **T**ampering | Malicious config | Config review; no remote config pull |
| **R**epudiation | “What did agent do?” | Explanations + feedback history + session summary |
| **I**nformation disclosure | Neural data leak | Local-first; no raw in logs; export strips samples; cloud LLM blocked by default |
| **D**enial of service | Agent spam / IoT loops | Rate limits, cooldowns, fail-safe, dry-run IoT |
| **E**levation | Agent does high-impact without consent | Impact tiers, confirm high-impact, fail-safe blocks IoT |

## Explicit non-goals (for now)

- Multi-tenant cloud hosting of neural data  
- Employer surveillance modes  
- Stimulation / write paths  

## Residual risks

1. Local malware has the same access as the user process.  
2. Screen-sharing may expose companion UI state.  
3. Enabling live IoT without dry-run can affect the physical environment.  
4. OS active-app detection may expose app titles locally (optional, off by default).  

## Controls checklist (release)

- [x] `local_only` default true  
- [x] Cloud LLM off; non-local URL blocked without allow flag  
- [x] IoT off + force dry-run default  
- [x] Fail-safe pause always available  
- [x] Profile export contains no raw neural samples  
- [x] CI enforces lint + tests on every PR (`.github/workflows/ci.yml`)  

## Reporting

See [SECURITY.md](../../SECURITY.md).
