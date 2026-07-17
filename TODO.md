# Neural Flow Architect — Build TODO

Living checklist for the public open-source foundation and early implementation.  
Check items as they ship. Prefer small, reviewable PRs.

**Legend:** `[x]` done in foundation · `[ ]` not started · `[~]` partial

---

## Phase 0 — Public foundation (this repo)

- [x] Repository structure and Apache-2.0 license
- [x] README with product vision, novelty, quick start
- [x] System architecture document + Mermaid diagrams
- [x] Architect agent design document
- [x] BCI adapter layer design (simulator → BrainFlow → Neuralink stub)
- [x] UX principles + wireframe descriptions
- [x] Privacy & ethics policy outline
- [x] Phased roadmap + Day-1 prototype plan
- [x] Novelty & differentiation summary
- [x] Open questions / risks
- [x] CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, NOTICE
- [x] `pyproject.toml`, `.gitignore`, `.env.example`
- [x] Core Python package skeleton (types, events, settings)
- [x] Simulator adapter + streaming loop
- [x] Baseline flow feature extraction + state machine
- [x] Rules-based Architect agent with explainability
- [x] Digital environment actions (notification policy, focus mode stubs)
- [x] Privacy consent + local session store stubs
- [x] CLI: `nfa demo`, `nfa stream`, `nfa status`
- [x] Unit tests for flow state machine + agent policies
- [x] Frontend scaffold (BCI-native layout stubs)
- [ ] CI workflow (lint, typecheck, test) on GitHub Actions
- [ ] Pre-commit config committed and documented
- [ ] First annotated public demo GIF / short video
- [ ] CODEOWNERS and issue/PR templates

---

## Phase 1 — MVP usable with open tools

### Signal & flow
- [ ] BrainFlow adapter with live board + file replay
- [ ] Quality metrics (impedance proxy, artifact flags, SNR heuristics)
- [ ] Multi-dimensional flow scores (engagement, arousal, self-ref proxy, confidence)
- [ ] Configurable band-power / connectivity feature set
- [ ] Session labeling UI (self-report: “I felt in flow”) for supervised personalization
- [ ] Graceful degradation when channels drop or quality is low

### Agent
- [ ] Tool registry with permission tiers (low / medium / high impact)
- [ ] Instant override channel (hotkey / neural command / voice)
- [ ] Preference learning from accept / reject / undo
- [ ] Explanation log exported with sessions
- [ ] Optional local LLM tool-calling backend (no cloud default)

### Environment
- [ ] OS notification suppression hooks (platform-specific modules)
- [ ] Focus mode: reduce UI chrome in companion UI
- [ ] Home Assistant integration behind explicit consent + `NFA_IOT_ENABLED`
- [ ] Safe action simulation mode (“dry run”) always available

### Product surface
- [ ] Local WebSocket API for state + explanations
- [ ] Companion UI: live flow indicator, explain drawer, override
- [ ] Post-session Flow Insights page (local only)
- [ ] Data export (JSON) with minimization options

### Quality
- [ ] Integration tests with fixture EEG
- [ ] Performance budget: end-to-end feature→state latency targets documented
- [ ] Accessibility audit checklist for companion UI

---

## Phase 2 — Full agentic co-pilot + personalization

- [ ] Multi-agent decomposition (Monitor, Protector, ReEntry, Explainer)
- [ ] Predictive intent-precursor layer (research-grade, off by default)
- [ ] Longitudinal personalization models per user profile
- [ ] Smart environment recipes (study, create, rest, social)
- [ ] Coaching plans (weekly gentle suggestions, user-gated)
- [ ] Context sources: active app (with OS permission), calendar optional
- [ ] Evaluation harness: offline replay of sessions + policy scores

---

## Phase 3 — High-bandwidth / Neuralink path

- [ ] Production adapter implementing high-level intent + feature streams
- [ ] Channel/count-agnostic pipeline stress tests (thousands of channels simulated)
- [ ] Low-latency path profiling and zero-copy buffers where needed
- [ ] Clinical/research partnership documentation (no PHI in public repo)
- [ ] Advanced predictive tools under strict consent + audit

---

## Long-term vision (post-Phase 3)

- [ ] Closed-loop stimulation hooks **only if** ethically approved APIs exist
- [ ] Multi-user research mode (federated / aggregate stats, no raw neural share by default)
- [ ] Robotic limb / wearable environment tools
- [ ] Apple BCI HID / industry standard HID bridges
- [ ] Formal regulatory pathway evaluation (if productizing as medical)

---

## Documentation debt

- [ ] Architecture Decision Records (ADRs) folder for major choices
- [ ] Contributor walkthrough video / text “first PR in 30 minutes”
- [ ] Glossary of flow science terms used in code
- [ ] Threat model document (STRIDE-lite for neural data)

---

## Community

- [ ] Public GitHub org/repo publish checklist
- [ ] Good first issues (at least 10)
- [ ] Discussion forum guidelines for implant users (privacy-aware)
- [ ] Research citation / related work page maintained quarterly

---

## Immediate next engineering tasks (suggested order)

1. Wire GitHub Actions CI  
2. Flesh out BrainFlow adapter with file replay fixtures  
3. Connect companion UI WebSocket to live `FlowState`  
4. Implement preference store + undo stack for agent actions  
5. Add self-report labeling for personalization v0  
6. Write ADR-0001: local-first privacy defaults  

---

*Last updated: foundation scaffold — July 2026*
