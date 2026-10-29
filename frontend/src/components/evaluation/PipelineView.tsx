import { ChevronRight, CircleDashed, CircleSlash, CircleCheck } from "lucide-react";
import { cn } from "../../lib/cn";
import type { PipelineRun } from "../../types/evaluation";
import { PIPELINE_STAGES, tracePipeline, type StageStatus } from "../../utils/pipelineTrace";

const STATUS: Record<StageStatus, { label: string; icon: typeof CircleCheck; className: string }> = {
  ran: { label: "Ran", icon: CircleCheck, className: "text-emerald-700" },
  skipped: { label: "Did not run", icon: CircleDashed, className: "text-slate-400" },
  stopped: { label: "Stopped here", icon: CircleSlash, className: "text-rose-700" },
};

/** Design reference only: says what each stage is for, never whether it ran. */
export function PipelineArchitecture() {
  return (
    <ol className="grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 sm:grid-cols-2 xl:grid-cols-6" aria-label="Pipeline design, in order">
      {PIPELINE_STAGES.map((stage, index) => (
        <li key={stage.id} className="relative bg-white px-4 py-3">
          <p className="flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
            <span className="tabular-nums">{index + 1}</span>
            {index < PIPELINE_STAGES.length - 1 ? <ChevronRight size={12} className="hidden xl:inline" aria-hidden /> : null}
          </p>
          <p className="mt-1 text-sm font-extrabold text-[#0b1f33]">{stage.title}</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">{stage.purpose}</p>
        </li>
      ))}
    </ol>
  );
}

function formatMs(ms: number): string {
  if (ms < 1) return "<1 ms";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`;
}

/** What actually happened for one live request, derived only from the API response. */
export function PipelineTraceView({ run }: { run: PipelineRun }) {
  const trace = tracePipeline(run);
  const total = run.timings?.total_ms;
  const timed = trace.filter((item) => item.ms !== null);
  const timedSum = timed.reduce((sum, item) => sum + (item.ms ?? 0), 0);
  return (
    <div>
      <ol className="divide-y divide-slate-200 rounded-2xl border border-slate-200 bg-white">
        {trace.map((item) => {
          const status = STATUS[item.status];
          return (
            <li key={item.stage.id} className="grid grid-cols-[1.25rem_1fr_auto] items-start gap-3 px-4 py-2.5">
              <status.icon size={18} className={cn("mt-0.5", status.className)} aria-hidden />
              <div className="min-w-0">
                <p className="text-sm font-bold text-[#0b1f33]">
                  {item.stage.title} <span className={cn("ml-1 text-xs font-bold", status.className)}>{status.label}</span>
                </p>
                <p className="text-xs leading-5 text-slate-600">{item.detail}</p>
              </div>
              <span className="text-right text-xs font-bold tabular-nums text-slate-700">{item.ms !== null ? formatMs(item.ms) : <span className="font-normal text-slate-400">—</span>}</span>
            </li>
          );
        })}
      </ol>
      {timed.length && timedSum > 0 ? (
        <div className="mt-3" aria-hidden>
          <div className="flex h-2 overflow-hidden rounded-full bg-slate-100">
            {timed.map((item, index) => (
              <span key={item.stage.id} className={cn("h-full", ["bg-slate-400", "bg-teal-700", "bg-[#0b1f33]"][index % 3])} style={{ width: `${((item.ms ?? 0) / timedSum) * 100}%` }} title={`${item.stage.title}: ${formatMs(item.ms ?? 0)}`} />
            ))}
          </div>
        </div>
      ) : null}
      <p className="mt-2 text-xs text-slate-500">
        {typeof total === "number" && total > 0 ? `Server-side total: ${formatMs(total)}. ` : ""}
        Timings come from the server. Stages without a timing are not measured separately; "Did not run" means the response shows the stage was skipped.
      </p>
    </div>
  );
}
