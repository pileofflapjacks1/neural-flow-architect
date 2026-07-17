/** Simple SVG sparkline for policy session scores (0–100). */

type Point = {
  score?: number | null;
  started_at?: string;
  session_id?: string;
};

type Props = {
  points: Point[];
  width?: number;
  height?: number;
  label?: string;
};

export function Sparkline({
  points,
  width = 320,
  height = 56,
  label = "Session policy scores",
}: Props) {
  if (!points.length) {
    return (
      <p className="dim" aria-label={`${label}: no data`}>
        No sparkline yet — complete a few sessions.
      </p>
    );
  }

  const scores = points.map((p) => Number(p.score ?? 0));
  const min = 0;
  const max = 100;
  const pad = 4;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;

  const coords = scores.map((s, i) => {
    const x =
      scores.length === 1
        ? pad + innerW / 2
        : pad + (i / (scores.length - 1)) * innerW;
    const y = pad + innerH - ((s - min) / (max - min)) * innerH;
    return { x, y, s };
  });

  const path = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  const last = scores[scores.length - 1];
  const first = scores[0];
  const trend =
    last - first >= 8 ? "up" : first - last >= 8 ? "down" : "flat";

  return (
    <div className="sparkline-wrap">
      <svg
        className="sparkline"
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${label}: ${scores.length} sessions, latest ${last.toFixed(0)}, trend ${trend}`}
      >
        <title>
          {label}: latest {last.toFixed(1)}/100 ({trend})
        </title>
        {/* baseline guides */}
        <line
          x1={pad}
          y1={pad + innerH}
          x2={pad + innerW}
          y2={pad + innerH}
          className="sparkline-axis"
        />
        <path d={path} className="sparkline-path" fill="none" />
        {coords.map((c, i) => (
          <circle
            key={points[i]?.session_id || i}
            cx={c.x}
            cy={c.y}
            r={scores.length > 10 ? 2.5 : 3.5}
            className="sparkline-dot"
          >
            <title>
              {points[i]?.started_at
                ? String(points[i].started_at).slice(0, 16)
                : `Session ${i + 1}`}
              : {c.s.toFixed(1)}
            </title>
          </circle>
        ))}
      </svg>
      <p className="meta-line sparkline-caption">
        {scores.length} session{scores.length === 1 ? "" : "s"} · latest{" "}
        <strong>{last.toFixed(0)}</strong>
        {trend === "up" ? " · trending up" : trend === "down" ? " · trending down" : ""}
      </p>
    </div>
  );
}
