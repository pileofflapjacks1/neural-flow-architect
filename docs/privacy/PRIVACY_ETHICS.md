# Privacy, Ethics & Safety Policy Outline

**Status:** Foundational policy for the open-source project  
**Applies to:** Code defaults, documentation, community practices

## 1. Classification

Neural Flow Architect is **research / assistive technology software**.

It is **not** a medical device and is **not** intended for diagnosis, treatment, cure, or prevention of disease unless and until appropriately regulated and cleared by relevant authorities.

## 2. Ethical north stars

1. **Agency** — Technology extends the user’s will; it does not substitute hidden goals.  
2. **Dignity** — Design for severe disability without paternalism.  
3. **Privacy** — Neural data is among the most intimate biometrics.  
4. **Transparency** — People must understand why the system acts.  
5. **Beneficence with humility** — Help flow; do not overclaim science.  
6. **Non-maleficence** — Avoid harm, coercion, lock-in, and unsafe automation.  

## 3. Data categories

| Category | Examples | Default handling |
|---|---|---|
| Raw neural samples | Multichannel voltages / spikes | Ephemeral RAM buffer; **not** persisted |
| Derived features | Band powers, model embeddings | Optional short retention with consent |
| Flow estimates | Scores, states, confidence | Session summaries with consent |
| Agent audit | Actions, explanations, undos | Local audit log with consent |
| Context | App titles, goals | Minimal; OS permission gated |
| Profile prefs | Thresholds, tool grants | Local profile |
| Identity | Name, email | Not required for core function |

## 4. Local-first principle

**Default:** All neural processing runs on the user’s machine.

- `NFA_LOCAL_ONLY=true`  
- `NFA_ALLOW_CLOUD_LLM=false`  
- No analytics SDK in default builds  
- Companion UI on localhost  

Any cloud feature must be:

1. Off by default  
2. Covered by granular consent  
3. Documented in UI before enable  
4. Unable to receive raw neural samples unless separately and explicitly consented (discouraged; generally refuse in design reviews)

## 5. Consent model

Consent is **granular, revocable, and logged**.

### Scopes (v1)

| Scope | Meaning |
|---|---|
| `acquire` | Read from BCI adapter |
| `process_realtime` | Features + flow estimates in memory |
| `persist_features` | Save features to disk |
| `persist_raw` | Save raw samples (discouraged; extra warning) |
| `agent_act` | Allow proactive tools |
| `iot_control` | Physical environment tools |
| `export` | Create export packages |
| `optional_llm` | Send **summaries only** to optional LLM backend |

Revocation takes effect **immediately** for future processing; UI offers deletion tools for retained data.

## 6. Minimization & retention

| Data | Default retention |
|---|---|
| Raw buffer | Seconds–minutes (ring) |
| Features | Session or ≤ 30 days if consented |
| Session summary | User-controlled; default 90 days |
| Audit log | 90 days |
| Exports | User-owned files; app does not re-upload |

Retention is configurable; **shorter is better**.

## 7. Transparency & explainability

- Real-time explanation of medium/high impact actions  
- Audit history browsable offline  
- Clear degraded-signal behavior  
- Public docs describing models’ limitations  

## 8. Safety requirements

### Must

- Instant global pause / override  
- Fail-safe idle on low confidence  
- Dry-run mode for environment actions  
- No disabling of emergency communication paths  
- Rate limits on physical actuators  
- Confirmation for high-impact tools by default  

### Must not

- Force continuous work against fatigue signals without user opt-in to “push” profiles  
- Hide agent activity  
- Punish opting out  
- Perform stimulation / write neural modulation in Phase 0–2  

## 9. Inclusive design & disability ethics

- Primary stakeholders include people with quadriplegia, ALS, and other severe motor impairments  
- UX optimized for low-precision control  
- Community spaces must not demand public disclosure of medical details  
- Caregivers may assist setup but should not silently receive neural data without the user’s consent  

## 10. Research use

If used in research:

- Follow institutional ethics / IRB requirements where applicable  
- Do not contribute identifiable neural data to the public repository  
- Prefer synthetic and consented open datasets with clear licenses  

## 11. Security baseline

- No secrets in git  
- Local API bound to `127.0.0.1` by default  
- Token for IoT stored in user keychain / env, not repo  
- Dependency pinning in releases  
- Security reports via [SECURITY.md](../../SECURITY.md)  

## 12. Legal / trademark

- Independent project; no implied endorsement by implant manufacturers  
- Users responsible for compliance with device ToS and local law  
- Contributors grant rights under Apache-2.0  

## 13. Policy changelog

Material privacy default changes require:

1. Docs update  
2. Migration notes  
3. Maintainer review labeled `privacy`  

## 14. Contact

Privacy concerns: use the security contact until a dedicated privacy address is published.
