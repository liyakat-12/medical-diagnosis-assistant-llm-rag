import { useId } from "react";

export type Series = { key: string; label: string; color: string };
export type BarGroup = { label: string; sublabel?: string; values: Record<string, number | null> };

const WIDTH = 720;
const HEIGHT = 300;
const PAD = { top: 22, right: 16, bottom: 72, left: 52 };

export function ChartLegend({ series }: { series: Series[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-bold text-slate-600" aria-hidden>
      {series.map((item) => (
        <li key={item.key} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: item.color }} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

export function GroupedBarChart({
  title,
  description,
  groups,
  series,
  max = 1,
  yLabel,
  format,
  ticks = [0, 0.25, 0.5, 0.75, 1],
}: {
  title: string;
  description: string;
  groups: BarGroup[];
  series: Series[];
  max?: number;
  yLabel: string;
  format: (value: number | null) => string;
  ticks?: number[];
}) {
  const id = useId();
  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const groupW = plotW / Math.max(groups.length, 1);
  const barGap = 4;
  const barW = Math.min(34, (groupW * 0.72 - barGap * (series.length - 1)) / series.length);
  const y = (value: number) => PAD.top + plotH - (Math.max(0, Math.min(value, max)) / max) * plotH;

  return (
    <figure className="min-w-0">
      <figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <span id={`${id}-title`} className="text-sm font-extrabold text-[#0b1f33]">
          {title}
        </span>
        <ChartLegend series={series} />
      </figcaption>
      <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full min-w-[44rem]" role="img" aria-labelledby={`${id}-title ${id}-desc`}>
        <desc id={`${id}-desc`}>{description}</desc>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(tick)} y2={y(tick)} className="stroke-slate-200" strokeDasharray={tick === 0 ? undefined : "3 4"} />
            <text x={PAD.left - 8} y={y(tick) + 4} textAnchor="end" className="fill-slate-500 text-[12px]">
              {format(tick)}
            </text>
          </g>
        ))}
        <text transform={`translate(14 ${PAD.top + plotH / 2}) rotate(-90)`} textAnchor="middle" className="fill-slate-500 text-[12px] font-bold">
          {yLabel}
        </text>
        {groups.map((group, groupIndex) => {
          const totalW = series.length * barW + (series.length - 1) * barGap;
          const start = PAD.left + groupIndex * groupW + (groupW - totalW) / 2;
          return (
            <g key={group.label}>
              {series.map((item, seriesIndex) => {
                const value = group.values[item.key];
                const x = start + seriesIndex * (barW + barGap);
                if (value === null || value === undefined) {
                  return (
                    <text key={item.key} x={x + barW / 2} y={PAD.top + plotH - 6} textAnchor="middle" className="fill-slate-400 text-[10px]">
                      n/a
                    </text>
                  );
                }
                return (
                  <g key={item.key}>
                    <rect x={x} y={y(value)} width={barW} height={PAD.top + plotH - y(value)} rx={3} fill={item.color} className="transition-opacity hover:opacity-80">
                      <title>{`${group.label} · ${item.label}: ${format(value)}`}</title>
                    </rect>
                    <text x={x + barW / 2} y={y(value) - 5} textAnchor="middle" className="fill-slate-700 text-[11px] font-bold">
                      {format(value)}
                    </text>
                  </g>
                );
              })}
              <text x={PAD.left + groupIndex * groupW + groupW / 2} y={HEIGHT - PAD.bottom + 18} textAnchor="middle" className="fill-[#0b1f33] text-[13px] font-bold">
                {group.label}
              </text>
              {group.sublabel ? (
                <text x={PAD.left + groupIndex * groupW + groupW / 2} y={HEIGHT - PAD.bottom + 34} textAnchor="middle" className="fill-slate-500 text-[11px]">
                  {group.sublabel}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      </div>
      <details className="mt-2 text-xs text-slate-600">
        <summary className="cursor-pointer font-bold text-slate-700">View as table</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <caption className="sr-only">{title}</caption>
            <thead>
              <tr className="border-b border-slate-200">
                <th scope="col" className="py-1 pr-3">Group</th>
                {series.map((item) => (
                  <th key={item.key} scope="col" className="py-1 pr-3">{item.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.label} className="border-b border-slate-100">
                  <th scope="row" className="py-1 pr-3 font-bold">{group.label}</th>
                  {series.map((item) => (
                    <td key={item.key} className="py-1 pr-3 tabular-nums">{format(group.values[item.key] ?? null)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

export function DistributionBars({ title, description, items, total }: { title: string; description: string; items: { label: string; value: number; tone: "good" | "warn" | "bad"; color?: string }[]; total: number }) {
  const id = useId();
  const tones = { good: "bg-teal-700", warn: "bg-slate-400", bad: "bg-amber-700" };
  return (
    <figure className="min-w-0" aria-labelledby={`${id}-title`} aria-describedby={`${id}-desc`}>
      <figcaption id={`${id}-title`} className="text-sm font-extrabold text-[#0b1f33]">
        {title}
      </figcaption>
      <p id={`${id}-desc`} className="sr-only">{description}</p>
      <ul className="mt-3 space-y-2.5">
        {items.map((item) => {
          const share = total ? item.value / total : 0;
          return (
            <li key={item.label} className="grid grid-cols-[minmax(5.5rem,7.5rem)_minmax(0,1fr)_auto] items-center gap-2 text-xs sm:gap-3">
              <span className="font-bold text-slate-700">{item.label}</span>
              <span className="h-2.5 overflow-hidden rounded-full bg-slate-100" title={`${item.label}: ${item.value} of ${total}`}>
                <span className={`block h-full rounded-full ${item.color ? "" : tones[item.tone]}`} style={{ width: `${Math.max(share * 100, item.value ? 1.5 : 0)}%`, background: item.color }} />
              </span>
              <span className="text-right font-bold tabular-nums text-slate-700">
                {item.value} <span className="font-normal text-slate-500">({(share * 100).toFixed(0)}%)</span>
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}

export type ColumnBar = { key: string; label: string; value: number | null; color: string };

/** HTML bars so labels stay readable when the card is narrow. Values are plotted from 0 to max. */
export function ColumnBars({
  title,
  description,
  yLabel,
  bars,
  format,
  max = 1,
  legend,
  footnote,
}: {
  title: string;
  description: string;
  yLabel: string;
  bars: ColumnBar[];
  format: (value: number | null) => string;
  max?: number;
  legend?: Series[];
  footnote?: string | null;
}) {
  const id = useId();
  const plotMin = Math.max(bars.length * 4.25, 12);
  return (
    <figure className="min-w-0" aria-labelledby={`${id}-title`} aria-describedby={`${id}-desc`}>
      <figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <span id={`${id}-title`} className="text-sm font-extrabold text-[#0b1f33]">{title}</span>
        {legend?.length ? <ChartLegend series={legend} /> : null}
      </figcaption>
      <p id={`${id}-desc`} className="sr-only">{description}</p>
      <div className="overflow-x-auto">
        <div className="w-full" style={{ minWidth: `${plotMin}rem` }}>
          <div className="grid grid-cols-[2.25rem_1fr] gap-x-2">
            <div className="flex h-36 flex-col justify-between text-right text-[10px] font-semibold text-slate-500" aria-hidden>
              <span>{format(max)}</span>
              <span>{format(max / 2)}</span>
              <span>{format(0)}</span>
            </div>
            <div className="flex h-36 items-end gap-2 border-b border-l border-slate-200 pl-2">
              {bars.map((bar) => {
                const fraction = bar.value === null ? 0 : Math.max(0, Math.min(bar.value, max)) / max;
                return (
                  <div key={bar.key} className="flex h-full min-w-0 flex-1 items-end">
                    <div
                      className="mx-auto w-full max-w-14 rounded-t-md motion-reduce:transition-none"
                      style={{ height: `${fraction * 100}%`, minHeight: bar.value ? 2 : 0, background: bar.value === null ? "transparent" : bar.color }}
                      title={`${bar.label}: ${bar.value === null ? "unavailable" : format(bar.value)}`}
                    />
                  </div>
                );
              })}
            </div>
            <div />
            <div className="mt-1.5 flex gap-2 pl-2">
              {bars.map((bar) => (
                <span key={bar.key} className="min-w-0 flex-1 text-center leading-4">
                  <span className="block text-[11px] font-bold text-slate-600">{bar.label}</span>
                  <span className="block text-[11px] font-bold tabular-nums text-[#0b1f33]">{bar.value === null ? "—" : format(bar.value)}</span>
                </span>
              ))}
            </div>
          </div>
          <ul className="sr-only">
            {bars.map((bar) => (
              <li key={bar.key}>{bar.label}: {bar.value === null ? "unavailable" : format(bar.value)}</li>
            ))}
          </ul>
        </div>
      </div>
      <p className="mt-2 text-[11px] font-bold text-slate-500">{yLabel}</p>
      {footnote ? <p className="mt-1 text-[11px] leading-4 text-slate-500">{footnote}</p> : null}
    </figure>
  );
}

export function HorizontalBars({
  title,
  description,
  items,
  format,
  max = 1,
}: {
  title: string;
  description: string;
  items: { label: string; value: number | null; detail?: string }[];
  format: (value: number | null) => string;
  max?: number;
}) {
  const id = useId();
  return (
    <figure className="min-w-0" aria-labelledby={`${id}-title`} aria-describedby={`${id}-desc`}>
      <figcaption id={`${id}-title`} className="text-sm font-extrabold text-[#0b1f33]">{title}</figcaption>
      <p id={`${id}-desc`} className="sr-only">{description}</p>
      <ul className="mt-3 max-h-72 space-y-3 overflow-y-auto pr-1">
        {items.map((item) => {
          const fraction = item.value === null ? 0 : Math.max(0, Math.min(item.value, max)) / max;
          return (
            <li key={item.label}>
              <div className="flex items-baseline justify-between gap-3 text-xs">
                <span className="min-w-0 font-bold text-slate-700">{item.label}</span>
                <span className="shrink-0 font-bold tabular-nums text-[#0b1f33]">{item.value === null ? "—" : format(item.value)}</span>
              </div>
              <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-100" title={`${item.label}: ${item.value === null ? "unavailable" : format(item.value)}${item.detail ? ` · ${item.detail}` : ""}`}>
                <div className="h-full rounded-full bg-teal-700" style={{ width: `${fraction * 100}%`, minWidth: item.value ? 2 : 0 }} />
              </div>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
