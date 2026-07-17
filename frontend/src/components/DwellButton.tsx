import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  label: string;
  onActivate: () => void;
  /** Dwell duration in ms */
  dwellMs?: number;
  disabled?: boolean;
  className?: string;
  /** variant styling */
  variant?: "primary" | "secondary" | "override" | "xl";
  /** When true, pointer/focus dwell is active */
  dwellEnabled?: boolean;
  /** External force-fill (e.g. scan highlight dwell) 0–1 */
  externalProgress?: number | null;
  "aria-pressed"?: boolean;
  title?: string;
};

/**
 * Large target with visual dwell fill for low-precision / implant dwell-select.
 * Completes when pointer stays over the control for dwellMs, or when
 * externalProgress reaches 1 (scan mode).
 */
export function DwellButton({
  label,
  onActivate,
  dwellMs = 1200,
  disabled = false,
  className = "",
  variant = "primary",
  dwellEnabled = true,
  externalProgress = null,
  ...aria
}: Props) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);
  const activeRef = useRef(false);
  const externalFiredRef = useRef(false);

  const clear = useCallback(() => {
    activeRef.current = false;
    startRef.current = null;
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    setProgress(0);
  }, []);

  const tick = useCallback(
    (now: number) => {
      if (!activeRef.current || startRef.current == null) return;
      const elapsed = now - startRef.current;
      const p = Math.min(1, elapsed / Math.max(dwellMs, 1));
      setProgress(p);
      if (p >= 1) {
        clear();
        onActivate();
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    },
    [clear, dwellMs, onActivate]
  );

  const begin = useCallback(() => {
    if (disabled || !dwellEnabled) return;
    if (activeRef.current) return;
    activeRef.current = true;
    startRef.current = performance.now();
    rafRef.current = requestAnimationFrame(tick);
  }, [disabled, dwellEnabled, tick]);

  useEffect(() => () => clear(), [clear]);

  // External scan dwell — fire once per completion edge
  useEffect(() => {
    if (externalProgress == null) {
      externalFiredRef.current = false;
      return;
    }
    setProgress(externalProgress);
    if (externalProgress < 1) {
      externalFiredRef.current = false;
      return;
    }
    // externalProgress >= 1: ScanMode owns activation when dwellEnabled={false}
    // Only auto-fire if we are not in pure display mode — parent handles run()
  }, [externalProgress]);

  const variantClass =
    variant === "secondary"
      ? "target-btn secondary"
      : variant === "override"
        ? "target-btn override"
        : variant === "xl"
          ? "target-btn target-xl"
          : "target-btn";

  const fill = externalProgress != null ? externalProgress : progress;

  return (
    <button
      type="button"
      className={`dwell-btn ${variantClass} ${className}`.trim()}
      disabled={disabled}
      onClick={() => {
        // Instant click still works (mouse/switch)
        clear();
        onActivate();
      }}
      onPointerEnter={begin}
      onPointerLeave={clear}
      onFocus={begin}
      onBlur={clear}
      aria-label={`${label}${dwellEnabled ? `, dwell ${dwellMs} milliseconds` : ""}`}
      {...aria}
    >
      <span
        className="dwell-fill"
        style={{ transform: `scaleX(${fill})` }}
        aria-hidden
      />
      <span className="dwell-label">{label}</span>
      {fill > 0 && fill < 1 && (
        <span className="dwell-pct" aria-hidden>
          {Math.round(fill * 100)}%
        </span>
      )}
    </button>
  );
}
