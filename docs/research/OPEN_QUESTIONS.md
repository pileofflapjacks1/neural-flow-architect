# Open Questions, Risks & Research Next Steps

Living document. Update as evidence arrives.

## 1. Scientific open questions

| ID | Question | Why it matters | Suggested next step |
|---|---|---|---|
| S1 | Which multi-dimensional constructs of “flow” are **identifiable** from open EEG vs intracortical data? | Avoid overclaiming; choose honest features | Literature review + labeled pilot with self-report |
| S2 | How stable are personal flow signatures across days, meds, fatigue, pain? | Personalization validity | Longitudinal n-of-1 protocols |
| S3 | What is the lag between neural precursors and conscious task switch intent? | Predictive layer feasibility | Controlled switch tasks with timestamps |
| S4 | Can we separate flow from mere high arousal / stress? | Safety and UX | Dual labeling: flow vs anxiety |
| S5 | How does decoder workload interact with flow in implant users? | BCI-specific confound | Collaborate with implant users on workload diaries |

## 2. Product / UX risks

| ID | Risk | Mitigation |
|---|---|---|
| U1 | Co-pilot itself becomes a distraction | Default calm; rate limits; disappear-in-flow UI |
| U2 | Users feel policed or infantilized | Tone guidelines; easy pause; no punishment |
| U3 | Over-suppression of notifications causes missed critical info | Allowlists; never block emergency channels |
| U4 | Dwell UI fatigue | Configurable timing; voice/multimodal |
| U5 | Insights induce unhealthy self-tracking pressure | Gentle copy; optional insights |

## 3. Technical risks

| ID | Risk | Mitigation |
|---|---|---|
| T1 | Vendor SDK access delays Phase 3 | Strong simulator + BrainFlow path; stub adapter |
| T2 | Latency regressions with high channel counts | Budget tests; feature-source short circuit |
| T3 | Non-determinism of LLM policies | Rules default; LLM sandboxed by governor |
| T4 | IoT unsafe actions | Dry-run, confirmations, rate limits |
| T5 | Fragmented OS notification APIs | Start with companion-level policy + documented OS hooks |

## 4. Privacy & ethics risks

| ID | Risk | Mitigation |
|---|---|---|
| E1 | Neural data leakage via logs/crash dumps | Structured logging bans raw samples; review checklists |
| E2 | Caregiver / third-party surveillance | User-owned consent; no silent sharing |
| E3 | Dual use (attention surveillance employers) | License + policy: personal agency tool; refuse covert workplace modes in core |
| E4 | Medical overclaim → harm | Hard disclaimer; no diagnostic UI |
| E5 | Future stimulation features | Separate ethics gate; not in early phases |

## 5. Community & governance risks

| ID | Risk | Mitigation |
|---|---|---|
| G1 | Scope creep into generic AI productivity app | Novelty filter in CONTRIBUTING / NOVELTY |
| G2 | Burnout of maintainers | Clear phase goals; shared ownership |
| G3 | Contribution of non-consensual datasets | Strict data policy in CONTRIBUTING |

## 6. Recommended research steps (near term)

1. **Annotated bibliography** of flow + EEG/BCI shared autonomy (quarterly).  
2. **Self-report protocol** v0 shipped with MVP for supervised labels.  
3. **n-of-1 evaluation harness**: replay sessions, score policy helpfulness.  
4. **UX interviews** with motor-impaired computer users (BCI and non-BCI).  
5. **Threat model** workshop (STRIDE-lite) before any network feature.  
6. **Ethics advisory** touchpoint before IoT physical actuation defaults loosen.  

## 7. Metrics to watch

- False protect rate (acted but user undid quickly)  
- Time-to-override (must stay tiny)  
- Signal-degraded idle compliance (must not act physically)  
- Install-to-first-demo time for new contributors  
- Doc drift vs code (architecture review each release)  

## 8. Decisions deferred

- Primary frontend framework long-term (React scaffold OK to replace)  
- Whether personalization models ship as ONNX only  
- Exact Neuralink API shape (stub until public/partner reality)  
- Governance model (BDFL vs steering committee) at larger scale  
