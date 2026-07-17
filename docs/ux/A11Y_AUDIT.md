# Accessibility audit checklist (BCI-native companion UI)

Use this when shipping UI changes or preparing a release.  
**Audience:** maintainers, caregivers, a11y reviewers, implant users giving feedback.

Related: [UX_PRINCIPLES.md](UX_PRINCIPLES.md) · [DAILY_DRIVER.md](DAILY_DRIVER.md) · [USER_GUIDE.md](USER_GUIDE.md)

---

## 0. Principles (always)

| # | Rule | Status target |
|---|---|---|
| P1 | Primary targets ≥ **64×64 CSS px** (scale with UI scale) | Required |
| P2 | **Pause** and **Undo** always available without deep navigation | Required |
| P3 | Fail-safe / errors use **assertive** live regions | Required |
| P4 | Routine status (signal, intents) use **polite** live regions (toggleable) | Required |
| P5 | Respect **reduced motion** and **high contrast** prefs | Required |
| P6 | No essential drag-only or hover-only actions | Required |
| P7 | Keyboard shortcuts never steal focus from text inputs | Required |
| P8 | Scan mode + dwell cover zero- / low-precision paths | Required |

---

## 1. Keyboard & focus order

| Check | How to verify | Pass? |
|---|---|---|
| Skip link “Skip to main content” appears on Tab | Keyboard only | ☐ |
| Skip link “Skip to primary controls” reaches Pause/Undo/Rest | Keyboard only | ☐ |
| Tab order: skip → sticky controls → banners → main → tabs/footer | Tab through page | ☐ |
| `:focus-visible` rings clear on buttons and tabs | Keyboard focus | ☐ |
| Sticky controls remain reachable while scrolling | Long session mock | ☐ |
| Shortcuts work when not in input: P F U R S X Y N 1–4 / | Keys | ☐ |
| Shortcuts **do not** fire in command bar / text fields | Type in input | ☐ |
| Scan mode: Space/Enter selects highlighted action | Enable Scan in Access | ☐ |
| Keyboard map listed under Access tab | Access → Keyboard map | ☐ |
| `GET /keymap` returns same intents as UI | `curl localhost:8741/keymap` | ☐ |

### Default keymap (summary)

| Key | Intent |
|---|---|
| **P** | Pause Architect |
| **F** | Resume Architect |
| **U** | Undo |
| **R** | Rest mode |
| **S** / **X** | Start / stop session |
| **Y** / **N** | Felt in flow / Not really |
| **1–4** | Study / Create / Rest / Social recipes |
| **/** | Why? |
| **H** | Help |
| **Space / Enter** | Select in scan mode |

Full list: Access tab or `GET /keymap`.

---

## 2. Screen reader & live regions

| Check | How to verify | Pass? |
|---|---|---|
| Fail-safe banner is `role="alert"` + assertive announcer | Trigger fail-safe or mock | ☐ |
| Connection/API error banner is assertive | Stop API while UI open | ☐ |
| Signal chip updates politely | Start/stop session | ☐ |
| Intent banner announces last intent | Press U / P | ☐ |
| “Announce actions” toggle in Access silences polite region | Toggle off | ☐ |
| Scan highlight change announced politely | Enable scan mode | ☐ |
| Dwell buttons have `aria-label` including dwell hint | Inspector / SR | ☐ |
| Decorative fill bars use `aria-hidden` | Inspector | ☐ |

---

## 3. Dwell & scan

| Check | How to verify | Pass? |
|---|---|---|
| Dwell presets: **800 / 1200 / 1800 ms** | Access chips | ☐ |
| Custom dwell 400–3000 ms saves | Access number field | ☐ |
| Click/tap still activates instantly | Click Pause | ☐ |
| Scan presets: **Fast 800 / Default 1400 / Slow 2000 ms** | Access chips | ☐ |
| Scan highlight visible (`.scan-active`) | Scan mode on | ☐ |
| Scan dwell auto-selects once (no double-fire) | Hold scan | ☐ |
| Reduced motion does not break dwell completion | Reduced motion on | ☐ |

---

## 4. Contrast, scale, motion

| Check | How to verify | Pass? |
|---|---|---|
| UI scale 1.0–1.75 enlarges targets (`--target-min`) | Access slider | ☐ |
| High contrast class applied to root/shell | Toggle | ☐ |
| Reduced motion reduces animation feel | Toggle + dwell fill | ☐ |
| Text remains readable at 200% browser zoom | Browser zoom | ☐ |
| Dark theme default (long sessions) | Visual | ☐ |

---

## 5. Multimodal & caregiver

| Check | How to verify | Pass? |
|---|---|---|
| Command bar phrases: pause, undo, rest, start session | Type commands | ☐ |
| Caregiver checklist available in Setup (full mode) | Tabs | ☐ |
| Profile export contains prefs only (no raw neural) | Export JSON | ☐ |
| Onboarding can be completed without mouse (keyboard) | First run | ☐ |

---

## 6. API surface (for automation)

| Endpoint | Expectation |
|---|---|
| `GET /a11y` | Includes `announce_actions`, `scan_*`, `keyboard_map`, presets |
| `POST /a11y` | Accepts scan_mode, scan_interval_ms, announce_actions, quiet hours |
| `GET /keymap` | Human-readable key → intent list |

```bash
curl -s http://127.0.0.1:8741/a11y | python -m json.tool | head
curl -s http://127.0.0.1:8741/keymap | python -m json.tool
curl -s -X POST http://127.0.0.1:8741/a11y \
  -H 'Content-Type: application/json' \
  -d '{"scan_interval_ms":800,"announce_actions":true}'
```

---

## 7. Automated / unit guards

```bash
pytest tests/unit/test_backup_a11y.py tests/unit/test_a11y_audit.py -q
```

| Guard | What it covers |
|---|---|
| `update_a11y` scan + announce | Persistence of a11y fields |
| Keymap non-empty | Intent vocabulary for UI |
| A11yBody accepts scan fields | API model not dropping posts |

---

## 8. Release sign-off

| Role | Date | Notes |
|---|---|---|
| Maintainer keyboard pass | | |
| Screen reader smoke (VoiceOver / NVDA) | | |
| Caregiver low-precision pass (trackpad dwell) | | |

**Not a medical certification.** This checklist supports assistive daily use of research software.

---

## Changelog (pack)

- Live announcer regions (assertive + polite)  
- Skip link to primary controls  
- Scan/dwell preset chips  
- Keyboard map in Access + `GET /keymap`  
- Full `A11yBody` fields (scan, quiet hours, announce)  
- Focus-visible CSS rings  
