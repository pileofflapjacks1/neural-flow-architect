import { useEffect, useRef, useState } from "react";
import { DwellButton } from "./DwellButton";

export type ScanAction = {
  id: string;
  label: string;
  run: () => void;
};

type Props = {
  enabled: boolean;
  intervalMs?: number;
  /** When > 0, highlighted item auto-selects after this dwell */
  dwellMs?: number;
  actions: ScanAction[];
  /** Use dwell-fill buttons even outside pure scan */
  dwellEnabled?: boolean;
};

/**
 * Sequential highlight scanning for zero-precision input.
 * - Space / Enter selects the highlighted action
 * - Optional dwell fill auto-selects when highlight holds for dwellMs
 */
export function ScanMode({
  enabled,
  intervalMs = 1400,
  dwellMs = 1200,
  actions,
  dwellEnabled = true,
}: Props) {
  const [index, setIndex] = useState(0);
  const [dwellProgress, setDwellProgress] = useState(0);
  const dwellStart = useRef<number | null>(null);
  const raf = useRef<number | null>(null);
  const indexRef = useRef(0);

  useEffect(() => {
    indexRef.current = index;
  }, [index]);

  // Advance highlight
  useEffect(() => {
    if (!enabled || actions.length === 0) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % actions.length);
      setDwellProgress(0);
      dwellStart.current = performance.now();
    }, intervalMs);
    dwellStart.current = performance.now();
    return () => window.clearInterval(id);
  }, [enabled, intervalMs, actions.length]);

  // Dwell fill on current highlight — fire once when full, then wait for next index
  useEffect(() => {
    if (!enabled || !dwellEnabled || actions.length === 0) return;
    dwellStart.current = performance.now();
    setDwellProgress(0);
    let fired = false;

    const tick = (now: number) => {
      if (dwellStart.current == null) return;
      const p = Math.min(1, (now - dwellStart.current) / Math.max(dwellMs, 1));
      setDwellProgress(p);
      if (p >= 1 && !fired) {
        fired = true;
        const i = indexRef.current;
        actions[i]?.run();
        // Hold full until scan advances; do not loop-fire
        return;
      }
      if (!fired) {
        raf.current = requestAnimationFrame(tick);
      }
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current != null) cancelAnimationFrame(raf.current);
    };
  }, [enabled, dwellEnabled, dwellMs, index, actions]);

  useEffect(() => {
    if (!enabled) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.code === "Space" || ev.code === "Enter") {
        const t = ev.target as HTMLElement | null;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
        ev.preventDefault();
        actions[index]?.run();
        dwellStart.current = performance.now();
        setDwellProgress(0);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, index, actions]);

  if (!enabled || actions.length === 0) return null;

  return (
    <section className="scan-mode" aria-label="Scan mode controls">
      <p className="meta-line">
        Scan + dwell — highlight fills, then selects · Space/Enter also selects
      </p>
      <div className="action-row">
        {actions.map((a, i) => (
          <DwellButton
            key={a.id}
            label={a.label}
            onActivate={() => a.run()}
            dwellMs={dwellMs}
            dwellEnabled={false}
            externalProgress={i === index ? dwellProgress : 0}
            variant={i === index ? "xl" : "secondary"}
            className={i === index ? "scan-active" : ""}
            aria-pressed={undefined}
          />
        ))}
      </div>
    </section>
  );
}
