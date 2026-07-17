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
- [x] CI workflow on GitHub Actions (lint, format, test, package)
- [x] Pre-commit config committed and documented
- [x] Local `scripts/ci.sh` mirrors Actions gates
- [ ] First annotated public demo GIF / short video
- [x] Issue/PR templates

---

## Phase 1 — MVP usable with open tools

### Signal & flow
- [x] BrainFlow adapter: live + synthetic board + CSV/NPY file mode + reconnect
- [x] Replay adapter + synthetic trajectory fixture
- [x] Fail-safe override (stall / quality / errors / user pause)
- [x] Action feedback (helpful / unhelpful / never) + affinity scoring
- [x] Active-app context (optional, local) + app-aware protect scoring
- [x] Adapter contract golden suite (`nfa contract`)
- [x] IoT force dry-run safety pack
- [x] Session trust metrics (`GET /trust`)
- [x] Threat model (STRIDE-lite)
- [x] Local audit log (JSONL, no raw neural)
- [x] Quiet hours soft policy
- [x] Soft recipe suggestions from app category
- [x] Trust panel + audit in Insights UI
- [x] `nfa report` CLI (+ `--json` scoreboard)
- [x] Version 0.2.0
- [x] End-of-block session review
- [x] Scan/dwell sequential control mode
- [x] Caregiver independence checklist
- [x] Personal flow signature v0
- [x] `nfa soak` long-session stability test
- [x] Good-first-issues list (docs/CONTRIBUTING_ISSUES.md)
- [x] Dwell-fill targets (Pause/Undo/Rest + scan auto-select)
- [x] Block-review → threshold/policy learning
- [x] User-editable app→category map (JSON + Insights UI)
- [x] OS Focus / DND hooks (dry-run default; Shortcuts / gsettings stubs)
- [x] Policy scoreboard (`GET /scoreboard`, Insights UI)
- [x] Session timeline (state/action/undo) API + UI
- [x] Quality metrics (clip/flat/noise/dropout heuristics + overall score)
- [x] Multi-dimensional flow scores (engagement, arousal, self-ref proxy, confidence)
- [x] Optional connectivity feature flag (`include_connectivity`)
- [x] Session labeling UI (self-report: “I felt in flow”) for supervised personalization
- [x] Graceful degradation when quality is low (idle_degraded + no IoT)
- [x] BrainFlow validation pack: `nfa doctor --brainflow`, file-mode pipeline tests, latency smoke
- [x] UI signal chip shows adapter name + quality overall

### Agent
- [x] Tool registry with permission tiers (low / medium / high impact)
- [x] Instant override channel (API + companion UI pause)
- [x] Preference learning from accept / reject / undo (Never / Allow always + undo stack)
- [x] Explanation log exported with sessions
- [x] Optional local LLM explanation wording (no cloud default; tool-calling later)

### Environment
- [x] OS notification suppression hooks (platform modules + null default)
- [x] Focus mode: reduce UI chrome in companion UI (in-process density/focus)
- [x] OS Focus / DND best-effort (`NFA_OS_FOCUS_*`, dry-run default)
- [x] Home Assistant optional integration (soft-fail; `NFA_IOT_ENABLED` + URL/token)
- [x] Safe action simulation mode (“dry run”) always available

### Product surface
- [x] Local WebSocket API for state + explanations (`nfa serve`)
- [x] Companion UI: live flow indicator, explain drawer, override
- [x] Post-session Flow Insights page (local only)
- [x] Data export (JSON) with minimization options (`/session/export`)

### Quality
- [x] Integration tests with fixture EEG (BrainFlow file mode closed loop)
- [x] Performance budget: feature→flow latency smoke in doctor + tests
- [ ] Accessibility audit checklist for companion UI

---

## Phase 2 — Full agentic co-pilot + personalization

- [x] Multi-agent decomposition (Protector, ReEntry, Transition + Explainer/Governor)
- [x] Predictive intent-precursor layer (research-grade, off by default)
- [x] Longitudinal personalization from self-report labels (threshold nudges)
- [x] Smart environment recipes (study, create, rest, social)
- [x] Coaching notes from local session history (gentle, non-medical)
- [x] Context enrichment: time of day, recipe, optional active_app / user_goal API
- [x] Evaluation harness: offline replay → policy scores (`nfa eval`)
- [x] Signal quality metrics + IoT stripped on low quality
- [x] Home Assistant optional REST path (soft-fail; enable via `NFA_IOT_ENABLED`)
- [x] Optional local LLM explanation wording (summaries only; Ollama/local URL)
- [x] OS notification hooks (null/macOS/Linux best-effort)
- [x] Latency budget docs + `nfa bench` (incl. high-channel stress)

---

## Phase 3 — High-bandwidth / Neuralink path

- [ ] Production adapter implementing high-level intent + feature streams
- [x] Channel/count-agnostic pipeline stress tests (`nfa bench --channels 256|1024`)
- [x] Low-latency path profiling (`nfa bench` + LATENCY_BUDGET.md); zero-copy later
- [ ] Clinical/research partnership documentation (no PHI in public repo)
- [x] Advanced predictive tools under strict consent + opt-in flag (heuristic v0)
- [x] Stable intent vocabulary + IntentRouter (pause/undo/rest/recipe/labels)
- [x] neuralink_stub cycles control intents for practice
- [x] Daily presets + first-run onboarding + Simple mode UI
- [x] `nfa start` / `nfa doctor` easy path + user/caregiver docs
- [x] Multimodal keyboard + voice/text → IntentRouter
- [x] A11y settings (scale, contrast, dwell) + profile export/import
- [x] Long-session buffer bounds + heartbeat/uptime + soft checkpoints
- [x] `nfa start --with-ui` optional combined launcher

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

1. ~~Wire GitHub Actions CI~~ done  
2. ~~BrainFlow validation pack~~ done  
3. Clear remaining mypy strict debt (make advisory CI job blocking)  
4. Annotated public demo GIF / short video  
5. Accessibility audit checklist for companion UI  
6. Timeline filter chips / scoreboard sparklines (Insights polish)  

---

*Last updated: BrainFlow validation pack — July 2026*
