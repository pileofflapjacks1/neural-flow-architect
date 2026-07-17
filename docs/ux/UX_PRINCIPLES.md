# UX Principles & Screen Flows

**Audience:** Designers, frontend contributors, accessibility reviewers, implant users giving feedback.

## 1. North star

The interface should **disappear during flow** and reappear as a calm, high-agency companion when needed.  
It must work for users with **severe motor impairment** using dwell selection, low-precision neural pointing, residual movement, and/or voice.

## 2. Principles

### P1 — BCI-native, not mouse-native shrunk down

- Minimum target size: **64×64 CSS px** (prefer 80+) for primary actions  
- Generous spacing; avoid dense icon rails  
- Dwell-friendly: clear hover/focus rings, configurable dwell time  
- No essential drag-and-drop only interactions  

### P2 — Low cognitive load

- One primary question per screen: *What is my state?* / *What is the Architect doing?* / *What should I change?*  
- Progressive disclosure for advanced settings  
- No gamified dopamine noise  

### P3 — Always explainable agency

- Every Architect action visible in an **Explain drawer**  
- Large persistent **Pause Architect** control  
- Status chip: `Protecting` | `Idle` | `Paused` | `Degraded signal`  

### P4 — Calm aesthetic for long sessions

- Neutral palette, low saturation by default  
- Optional high-contrast mode  
- Motion: minimal; respect `prefers-reduced-motion`  
- Dark mode first-class (long night sessions)  

### P5 — Multimodal input

- Neural dwell / select  
- Voice commands for pause/resume/focus  
- Keyboard / switch / residual motor where available  
- Never voice-only for safety actions  

### P6 — Accessibility

- WCAG 2.2 AA target for companion UI  
- Full screen reader labels  
- Focus order logical; skip links  
- Captions for any audio coaching  

### P7 — Trust & non-manipulation

- No dark patterns to extend session length  
- Fatigue state suggests rest, not “push harder” by default  
- Clear **not a medical device** notice in About  

## 3. Information architecture

```text
App Shell
├── Today (live session)
│   ├── Flow ring / state
│   ├── Architect status + Pause
│   └── Latest explanation
├── Insights
│   ├── Session summary
│   └── Longitudinal patterns
├── Environment
│   ├── Digital policies
│   └── IoT (if enabled)
├── Preferences
│   ├── Sensitivity / thresholds
│   ├── Tool permissions
│   └── Consent & data
└── About / Safety
```

## 4. Wireframe descriptions

### 4.1 Live session (default)

```
┌──────────────────────────────────────────────────────────────┐
│  Neural Flow Architect          ● Signal good    [Pause ▉▉]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│              ┌─────────────────────┐                         │
│              │     FLOW  0.78      │                         │
│              │   state: flow       │                         │
│              │   12 min in state   │                         │
│              └─────────────────────┘                         │
│                                                              │
│  Architect: Protecting focus                                 │
│  “I simplified the UI and suppressed non-critical            │
│   notifications because engagement is rising (12 min).”      │
│                                                              │
│  [ Undo last ]     [ Why? ]     [ Rest mode ]                │
│                                                              │
│  Dimensions:  Engagement ████████░░  Ease ███████░░░         │
└──────────────────────────────────────────────────────────────┘
```

Notes:

- Pause control always visible, high contrast  
- Undo is first-class  
- Dimensions are secondary, not a scientific dashboard by default  

### 4.2 Degraded signal

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠ Signal degraded — proactive actions limited     [Pause]   │
│  Architect is idle for safety. You remain in full control.   │
│  [ Troubleshooting ]                                         │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 Explain drawer

```
┌─────────────────────────────┐
│ Why did this happen?        │
│                             │
│ Action: suppress notices    │
│ Time: 14:02                 │
│                             │
│ Signals:                    │
│  • engagement 0.82 ↑        │
│  • state: flow              │
│  • quality 0.91             │
│                             │
│ [ Allow always ] [ Never ]  │
└─────────────────────────────┘
```

### 4.4 Insights (post-session)

```
┌──────────────────────────────────────────────────────────────┐
│ Session · 1h 42m                                             │
│ Time in flow: 47m  · Deep flow: 11m  · Breaks: 3             │
│                                                              │
│ Best stretch: 10:15–10:40 (study)                            │
│ Helpful actions: dim lights (accepted), quiet notify (undo×1)│
│                                                              │
│ Gentle note: Your flow often starts 20–40 min after          │
│ beginning a labeled study block.                             │
│                                                              │
│ [ Export summary ]  [ Delete session ]                       │
└──────────────────────────────────────────────────────────────┘
```

### 4.5 Consent & data

Large toggles, plain language:

- Process signals on this device  
- Save session summaries  
- Save detailed features  
- Allow smart home control  
- Allow optional local AI wording  

Each toggle shows **what is stored**, **where**, and **how to delete**.

## 5. Interaction patterns

| Pattern | Spec |
|---|---|
| Dwell select | Configurable 0.8–2.0 s; visual fill indicator |
| Confirm high impact | Two-step or long-dwell confirm |
| Undo | Available ≥ 30 s for reversible actions |
| Voice | “Pause architect”, “Resume architect”, “Rest mode” |
| Errors | Plain language, next action, no stack traces in UI |

## 6. Visual design tokens (suggested)

```text
--bg: #0f1218
--surface: #1a2030
--text: #e8ecf4
--muted: #9aa6bf
--accent: #6ea8ff
--good: #3ecf8e
--warn: #f0b429
--danger: #ff6b6b
--target-min: 64px
--radius: 16px
--font: system-ui, "Segoe UI", sans-serif
```

Aesthetic: **calm instrument panel**, not consumer fitness gamification.

## 7. Frontend stack (scaffold)

- `frontend/` Vite + TypeScript + React (or swap to Svelte — keep contracts)  
- Talks to local API `ws://127.0.0.1:8741/ws/state`  
- No telemetry by default  

## 8. UX research backlog

- Dwell timing study with motor-impaired users  
- Explanation length vs trust  
- How often protect actions feel helpful vs patronizing  
- Night-time fatigue UX  

## 9. Inclusive language

Prefer:

- “User”, “person”, “you”  
- “Estimated flow-related state”  
- “Pause co-pilot”  

Avoid:

- “Patient” in product UI (unless clinical deployment context)  
- “Broken”, “normal brain” comparisons  
- Guaranteed clinical outcomes  
