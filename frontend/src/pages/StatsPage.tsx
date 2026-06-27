import { useQuery } from "@tanstack/react-query";

import { getFilesStats, getTagsStats } from "../api/stats";
import Spinner from "../components/common/Spinner";
import type { Bucket } from "../types";
import styles from "./css/StatsPage.module.css";

const PALETTE = [
  "#6c5ce7",
  "#00b894",
  "#0984e3",
  "#fdcb6e",
  "#e17055",
  "#e84393",
  "#00cec9",
  "#a29bfe",
];

function pct(value: number, total: number): string {
  if (total <= 0 || value <= 0) return "0%";
  const exact = (value / total) * 100;
  // Don't round a real, non-zero share down to "0%".
  if (exact < 1) return "<1%";
  return `${Math.round(exact)}%`;
}

/* --- Donut ---------------------------------------------------------------- */
function Donut({
  data,
  colors,
  centerLabel,
}: {
  data: Bucket[];
  colors?: string[];
  centerLabel?: string;
}) {
  const palette = colors ?? PALETTE;
  const total = data.reduce((acc, item) => acc + item.count, 0);
  const size = 132;
  const thickness = 20;
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div className={styles.donutWrap}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={styles.donut}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--color-surface-2)"
            strokeWidth={thickness}
          />
          {data.map((item, index) => {
            const frac = total > 0 ? item.count / total : 0;
            const len = frac * c;
            const dash = (
              <circle
                key={item.label}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={palette[index % palette.length]}
                strokeWidth={thickness}
                strokeDasharray={`${len} ${c - len}`}
                strokeDashoffset={-offset}
              />
            );
            offset += len;
            return dash;
          })}
        </g>
        <text x="50%" y="47%" className={styles.donutTotal} textAnchor="middle">
          {total.toLocaleString()}
        </text>
        {centerLabel && (
          <text x="50%" y="61%" className={styles.donutCaption} textAnchor="middle">
            {centerLabel}
          </text>
        )}
      </svg>
      <ul className={styles.legend}>
        {data.map((item, index) => (
          <li key={item.label} className={styles.legendItem}>
            <span
              className={styles.legendDot}
              style={{ backgroundColor: palette[index % palette.length] }}
            />
            <span className={styles.legendLabel}>{item.label}</span>
            <span className={styles.legendValue}>{pct(item.count, total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* --- Smooth area/line graph ---------------------------------------------- */
interface Point {
  x: number;
  y: number;
}

function controlPoint(current: Point, previous: Point, next: Point, reverse: boolean): Point {
  const prev = previous || current;
  const nxt = next || current;
  const smoothing = 0.2;
  const dx = nxt.x - prev.x;
  const dy = nxt.y - prev.y;
  const angle = Math.atan2(dy, dx) + (reverse ? Math.PI : 0);
  const length = Math.hypot(dx, dy) * smoothing;
  return { x: current.x + Math.cos(angle) * length, y: current.y + Math.sin(angle) * length };
}

function smoothLine(points: Point[]): string {
  return points.reduce((acc, point, i, arr) => {
    if (i === 0) return `M ${point.x},${point.y}`;
    const start = controlPoint(arr[i - 1], arr[i - 2] ?? arr[i - 1], point, false);
    const end = controlPoint(point, arr[i - 1], arr[i + 1] ?? point, true);
    return `${acc} C ${start.x},${start.y} ${end.x},${end.y} ${point.x},${point.y}`;
  }, "");
}

function AreaGraph({ data, color }: { data: Bucket[]; color: string }) {
  const w = 320;
  const h = 150;
  const padX = 14;
  const padTop = 16;
  const padBottom = 28;
  const max = data.reduce((acc, item) => Math.max(acc, item.count), 0) || 1;
  const innerW = w - padX * 2;
  const innerH = h - padTop - padBottom;
  const step = data.length > 1 ? innerW / (data.length - 1) : 0;

  const points: Point[] = data.map((item, i) => ({
    x: padX + i * step,
    y: padTop + innerH - (item.count / max) * innerH,
  }));

  const line = smoothLine(points);
  const area = `${line} L ${padX + innerW},${padTop + innerH} L ${padX},${padTop + innerH} Z`;
  const baseline = padTop + innerH;

  return (
    <div className={styles.graph}>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.graphSvg} preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.35" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.5, 1].map((g) => (
          <line
            key={g}
            x1={padX}
            x2={padX + innerW}
            y1={padTop + innerH * (1 - g)}
            y2={padTop + innerH * (1 - g)}
            className={styles.graphGrid}
          />
        ))}
        <line x1={padX} x2={padX + innerW} y1={baseline} y2={baseline} className={styles.graphAxis} />
        <path d={area} fill="url(#areaFill)" />
        <path d={line} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" />
        {points.map((point, i) => (
          <g key={data[i].label}>
            <circle cx={point.x} cy={point.y} r={3.5} fill="var(--color-surface)" stroke={color} strokeWidth={2} />
            <text x={point.x} y={point.y - 9} className={styles.graphValue} textAnchor="middle">
              {data[i].count.toLocaleString()}
            </text>
            <text x={point.x} y={baseline + 16} className={styles.graphLabel} textAnchor="middle">
              {data[i].label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

/* --- Colored bars --------------------------------------------------------- */
function ColorBars({ data, colors }: { data: Bucket[]; colors?: string[] }) {
  const palette = colors ?? PALETTE;
  const max = data.reduce((acc, item) => Math.max(acc, item.count), 0) || 1;
  return (
    <div className={styles.bars}>
      {data.map((item, index) => (
        <div key={item.label} className={styles.barRow}>
          <span className={styles.barLabel}>{item.label}</span>
          <div className={styles.barTrack}>
            <div
              className={styles.barFill}
              style={{
                width: `${(item.count / max) * 100}%`,
                backgroundColor: palette[index % palette.length],
              }}
            />
          </div>
          <span className={styles.barValue}>{item.count.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className={styles.metric}>
      <span className={styles.metricDot} style={{ backgroundColor: accent }} />
      <div className={styles.metricBody}>
        <span className={styles.metricValue}>{value}</span>
        <span className={styles.metricLabel}>{label}</span>
      </div>
    </div>
  );
}

export default function StatsPage() {
  const filesQuery = useQuery({ queryKey: ["stats-files"], queryFn: getFilesStats });
  const tagsQuery = useQuery({ queryKey: ["stats-tags"], queryFn: getTagsStats });

  if (filesQuery.isLoading || tagsQuery.isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.state}>
          <Spinner /> Loading statistics…
        </div>
      </div>
    );
  }

  if (filesQuery.isError || tagsQuery.isError || !filesQuery.data || !tagsQuery.data) {
    return (
      <div className={styles.page}>
        <div className={styles.error}>Couldn&apos;t load statistics.</div>
      </div>
    );
  }

  const files = filesQuery.data;
  const tags = tagsQuery.data;
  const untagged = Math.max(files.total - tags.tagged_total, 0);

  const tagStatus: Bucket[] = [
    { label: "passed", count: tags.passed },
    { label: "failed", count: tags.failed },
    { label: "untagged", count: untagged },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.metrics}>
        <MetricCard label="Total images" value={files.total.toLocaleString()} accent="#6c5ce7" />
        <MetricCard label="You tagged" value={tags.tagged_total.toLocaleString()} accent="#00b894" />
        <MetricCard label="Your labels" value={tags.labels.length.toLocaleString()} accent="#0984e3" />
        <MetricCard
          label="Avg agreement"
          value={`${Math.round(files.agreement.avg * 100)}%`}
          accent="#e84393"
        />
        <MetricCard
          label="Avg caption length"
          value={`${files.caption_length.avg}w`}
          accent="#fdcb6e"
        />
      </div>

      <div className={styles.grid}>
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Images by split</h2>
          <Donut data={files.by_split} centerLabel="images" />
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Orientation</h2>
          <Donut
            data={files.by_orientation}
            colors={["#0984e3", "#00b894", "#fdcb6e"]}
            centerLabel="images"
          />
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Your tagging progress</h2>
          <Donut data={tagStatus} colors={["#00b894", "#e17055", "#b2bec3"]} centerLabel="images" />
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Annotator agreement</h2>
          <AreaGraph data={files.agreement.buckets} color="#6c5ce7" />
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Caption length</h2>
          <AreaGraph data={files.caption_length.buckets} color="#0984e3" />
        </section>

        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Your top labels</h2>
          {tags.labels.length === 0 ? (
            <p className={styles.cardHint}>No labels yet. Add labels from the Explorer.</p>
          ) : (
            <ColorBars
              data={[...tags.labels].sort((a, b) => b.count - a.count).slice(0, 6)}
            />
          )}
        </section>
      </div>
    </div>
  );
}
