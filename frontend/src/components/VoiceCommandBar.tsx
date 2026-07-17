import { useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Props = {
  enabled?: boolean;
};

export function VoiceCommandBar({ enabled = true }: Props) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  if (!enabled) return null;

  const submit = async () => {
    if (!text.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/input/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: "voice", text }),
      });
      const data = await res.json();
      if (data.ok) {
        setStatus(`OK: ${data.parsed?.intent ?? "command"}`);
        setText("");
      } else {
        setStatus(data.message || "Not recognized");
      }
    } catch {
      setStatus("API offline");
    }
  };

  return (
    <section className="voice-bar" aria-label="Voice or typed command">
      <label htmlFor="voice-cmd" className="meta-line">
        Say or type a command (e.g. “pause”, “undo”, “rest mode”)
      </label>
      <div className="action-row">
        <input
          id="voice-cmd"
          className="voice-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="pause architect"
          autoComplete="off"
        />
        <button type="button" className="target-btn secondary" onClick={submit}>
          Go
        </button>
      </div>
      {status && (
        <p className="meta-line" role="status">
          {status}
        </p>
      )}
    </section>
  );
}
