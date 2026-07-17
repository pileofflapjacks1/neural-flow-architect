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

## Accessibility

Open **Access** tab (full mode) or API `POST /a11y`:

- UI scale  
- High contrast  
- Reduced motion  
- Dwell ms (for future dwell widgets)  
- Keyboard / command bar toggles  
- Profile export backup (preferences only — **no raw neural data**)

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
