# Daily Driver — Long Sessions & Multimodal Control

For people who may use a computer **many hours per day** via BCI.

## Reliability

| Feature | Behavior |
|---|---|
| Bounded signal buffers | Feature extractor caps memory for multi-hour runs |
| Session health | Live `uptime_sec` + tick count in companion UI |
| Periodic checkpoint | Profile soft-save during long sessions |
| Local-first | No cloud required for core loop |

## Multimodal control (same intents as implant)

Everything routes through the shared **IntentRouter**:

| Source | How |
|---|---|
| Implant intents | Adapter `IntentEvent` stream |
| Keyboard | `P` pause · `F` resume · `U` undo · `R` rest · `S` start · `Y`/`N` labels · `1–4` recipes |
| Voice / type | Command bar: “pause”, “undo”, “rest mode”, … |
| UI buttons | Sticky Pause · Undo · Rest |

## Dwell fill (implant-friendly select)

Primary controls (**Pause · Undo · Rest**) show a **fill bar** while the pointer
or focus stays on the target. When the bar completes (default ~1200 ms from
Access → Dwell fill ms), the action fires.

- **Click / tap** still activates immediately  
- **Scan mode** fills the highlighted control, then selects  
- **Space / Enter** still select in scan mode  

Tune dwell under **Access**. Respects reduced-motion (no fancy animation curves).

## End-of-block review → learning

When you **Stop session**, a short review asks if the block (and co-pilot) helped.

| Answer | Learning effect |
|---|---|
| Yes, helpful | Slightly ease flow-entry thresholds; reinforce protect tools |
| Block OK, co-pilot noisy | Force **calm** protect style; penalize suppress/focus cooldowns |
| Not really | Raise thresholds; calm style |
| Skip | No threshold change |

Reviews also feed the personal flow signature (`GET /signature`).

## Policy scoreboard, weekly recap & timeline

Open **Insights** (full mode) for:

| Panel | Source |
|---|---|
| **This week** | `GET /weekly?days=7` — window chips 7/14/30d, sparkline, highlights |
| **Session recap** | `GET /session/recap` — helped / hurt / recommendations for current or last session |
| **Hybrid flow ML** | `GET /flow/ml` — train status from local “Felt in flow” labels |
| Policy scoreboard | `GET /scoreboard` — undos, block reviews, trust → 0–100 + recent sparkline |
| Session timeline | `GET /timeline` — filter chips: All / State / Action / Undo |
| App → category map | `GET/POST /app_map` — local JSON overrides for active-app recipes |
| OS Focus / DND | `GET/POST /os_focus` — dry-run default; live only when enabled |

CLI:

```bash
nfa report                 # trust + scoreboard + this-week highlights
nfa report --json --days 14
```

No raw neural data in reports.

## Accessibility

Open **Access** tab (full mode) or API `POST /a11y`:

- UI scale  
- High contrast  
- Reduced motion  
- Screen reader announcements (polite live region)  
- Dwell fill presets: **800 / 1200 / 1800 ms**  
- Scan mode + interval presets: **Fast 800 / Default 1400 / Slow 2000 ms**  
- Keyboard map (and `GET /keymap`)  
- Keyboard / command bar toggles  
- Profile export backup (preferences only — **no raw neural data**)  

Release checklist: [A11Y_AUDIT.md](A11Y_AUDIT.md).

## Easy start with UI

```bash
nfa start --with-ui
# or
nfa start --open
```

## Practice implant intents without hardware

```bash
nfa serve --adapter neuralink_stub
```

Stub cycles high-confidence control intents so you can verify Pause/Undo/Rest paths end-to-end.
