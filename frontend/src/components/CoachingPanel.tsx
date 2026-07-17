import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_NFA_API ?? "http://127.0.0.1:8741";

type Note = { title: string; body: string; kind: string };

export function CoachingPanel() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/coaching`)
      .then((r) => r.json())
      .then((data) => setNotes(data.notes || []))
      .catch(() => setError("Could not load coaching notes"));
  }, []);

  if (error) {
    return <p className="explanation">{error}</p>;
  }

  return (
    <section className="coaching">
      <h2>Gentle coaching</h2>
      <p className="dim">
        Local suggestions from your session history — not medical advice.
      </p>
      <ul className="coaching-list">
        {notes.map((n, i) => (
          <li key={i}>
            <strong>{n.title}</strong>
            <p>{n.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
