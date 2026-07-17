# Good first issues (suggested)

Use these labels when filing issues on GitHub: `good first issue`, `docs`, `bci-ux`, `privacy`, `flow-science`.

## Starter issues for new contributors

1. **docs:** Add a screenshot placeholder section to README for companion UI.  
2. **bci-ux:** Increase default scan interval options in Access panel (presets 800/1400/2000 ms).  
3. **adapters:** Add OpenBCI Ganglion board_id note to `docs/bci/BRAINFLOW.md`.  
4. **tests:** Property test that fail-safe always allows `notify.allow_all`.  
5. **i18n:** Extract sticky control labels (Pause/Undo/Rest) to a constants file.  
6. **privacy:** Add unit test that audit log never accepts a `data` detail key.  
7. **flow-science:** Document that engagement_proxy is not clinical flow.  
8. **frontend:** Timeline filter chips (state / action / undo only).  
9. **os-focus:** Windows Focus Assist bridge (still dry-run safe by default).  
10. **scoreboard:** Sparkline of policy score across last N sessions.  
11. **a11y:** VoiceOver / NVDA walkthrough notes added to A11Y_AUDIT sign-off.  

## Design constraints for all issues

- Local-first defaults  
- User override always available  
- No raw neural data in git or default logs  
- Adapter boundary preserved  
