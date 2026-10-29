import { cn } from "../../lib/cn";
import type { RetrievalRun } from "../../types/evaluation";
import { retrievalMetricCards } from "../../utils/evaluationCharts";

const ACCENTS = { teal: "bg-teal-700", navy: "bg-[#0b1f33]", slate: "bg-slate-300" };

export function MetricCards({ run }: { run: RetrievalRun }) {
  const cards = retrievalMetricCards(run);
  return (
    <div>
      <p className="sr-only" aria-live="polite">
        Metrics for {run.label}
      </p>
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {cards.map((item) => (
          <div key={item.label} data-metric={item.label} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
            <dt className="text-xs font-bold text-slate-500">{item.label}</dt>
            <dd className="mt-1.5 text-2xl font-extrabold tabular-nums tracking-tight text-[#0b1f33] sm:text-3xl">
              {item.value}
              {item.unavailable ? <span className="sr-only"> unavailable</span> : null}
            </dd>
            <dd aria-hidden className={cn("mt-3 h-1 w-8 rounded-full", ACCENTS[item.accent])} />
          </div>
        ))}
      </dl>
    </div>
  );
}
