# Demo media

Annotated companion-UI walkthrough for README and docs.

| File | Description |
|---|---|
| `nfa-companion-demo.gif` | 4-frame loop (~2.4s/frame): live session → dwell fill → Why? → weekly recap |
| `demo-hero.png` | Still of live session (frame 1) |
| `demo-frame-1.png` … `demo-frame-4.png` | Individual annotated stills |

## Storyboard

1. **Live session** — flow ring, signal chip, Pause / Undo / Rest, “Protecting your focus”  
2. **Dwell fill** — hold-to-select without a click (BCI-friendly)  
3. **Why?** — explainable actions + Helpful / Not helpful / Never feedback  
4. **This week** — local policy score, sparkline, timeline filters (no raw neural data)  

## Notes

- These are **product mockups** of the companion UI concept for marketing/onboarding, not screen captures of a specific commit.  
- Always label demos as **research / assistive software — not a medical device**.  
- Prefer GIF under ~1 MB for GitHub README load times (current target ~0.5 MB).  

## Regenerate (maintainers)

Frames are assembled with Pillow from design exports. To rebuild after new stills:

```bash
# Place source frames, then run an assembly script or:
python -c "from PIL import Image; ..."
```

For a live capture later: run `nfa start --with-ui`, record with your OS screen tool, export GIF/WebM, replace files here.
