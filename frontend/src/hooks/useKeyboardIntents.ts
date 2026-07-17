import { useEffect } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

/**
 * Global keyboard → IntentRouter bridge.
 * Skips when focus is in inputs so typing is not stolen.
 */
export function useKeyboardIntents(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;

    const onKey = (ev: KeyboardEvent) => {
      if (ev.metaKey || ev.ctrlKey || ev.altKey || ev.shiftKey) return;
      const target = ev.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }
      // Don't steal browser refresh etc. — only our codes
      const allowed = new Set([
        "KeyP",
        "KeyU",
        "KeyR",
        "KeyS",
        "KeyX",
        "KeyY",
        "KeyN",
        "KeyF",
        "KeyH",
        "Slash",
        "Digit1",
        "Digit2",
        "Digit3",
        "Digit4",
      ]);
      if (!allowed.has(ev.code)) return;
      ev.preventDefault();
      fetch(`${API_BASE}/input/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "keyboard", code: ev.code }),
      }).catch(() => {
        /* ignore offline */
      });
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}
