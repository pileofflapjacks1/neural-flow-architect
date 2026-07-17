# Fail-safe override

Proactivity must never trap the user. Fail-safe is **always stronger** than the Architect.

## Triggers

| Trigger | Effect |
|---|---|
| **User Pause** | Immediate idle; IoT disabled |
| **Stream stall** (~3s no frames) | Fail-safe active; block medium/high/IoT |
| **Low quality streak** | Fail-safe active; block protect tools |
| **Agent tool errors** | After repeated errors, halt proactive tools |

## Always available

- `POST /agent/pause` — works even when the loop is degraded  
- Sticky UI **Pause · Undo · Rest**  
- Intent / keyboard / voice → same pause path  
- Restore-only tools may still run (`notify.allow_all`, `focus.disable`)

## Clear

`POST /agent/failsafe/clear` after signal recovers (not while user-paused).

## Design rule

> If the user cannot stop the co-pilot in one large target or one intent, the release is blocked.
