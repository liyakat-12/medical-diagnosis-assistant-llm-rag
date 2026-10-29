import { useMemo, useState, type FormEvent } from "react";
import { FlaskConical, Play, ShieldAlert } from "lucide-react";
import { cn } from "../../lib/cn";
import type { RetrievalCase } from "../../types/evaluation";
import { pickDemoCases, type DemoCase } from "../../utils/demoCases";
import { OutcomeBadge } from "./RankLadder";
import { LiveRunView, useLiveRun } from "./LiveRun";

const MAX_QUERY = 1000;

export function DemoMode({ cases, depth }: { cases: RetrievalCase[]; depth: number }) {
  const samples = useMemo(() => pickDemoCases(cases, depth), [cases, depth]);
  const [selectedKey, setSelectedKey] = useState(samples[0]?.key ?? "");
  const live = useLiveRun(depth);
  const selected = samples.find((item) => item.key === selectedKey) ?? samples[0];

  const choose = (sample: DemoCase) => {
    setSelectedKey(sample.key);
    live.reset();
  };

  return (
    <div>
      <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        <FlaskConical size={18} className="mt-0.5 shrink-0 text-amber-700" aria-hidden />
        <p className="leading-6">
          <span className="font-extrabold">Synthetic sample cases.</span> These queries were written for evaluation; they are not patient data. Each one runs through the real retrieval index and the real answer pipeline. Nothing is saved to any account or chat.
        </p>
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[18rem_1fr]">
        <fieldset className="min-w-0">
          <legend className="text-xs font-extrabold uppercase tracking-wider text-slate-500">Sample cases</legend>
          <ul className="mt-2 space-y-1.5">
            {samples.map((sample) => {
              const active = sample.key === selected?.key;
              return (
                <li key={sample.key}>
                  <button
                    type="button"
                    onClick={() => choose(sample)}
                    aria-pressed={active}
                    className={cn(
                      "w-full rounded-xl border px-3 py-2 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-700",
                      active ? "border-teal-700 bg-teal-50" : "border-slate-200 bg-white hover:border-slate-300",
                    )}
                  >
                    <span className="line-clamp-2 text-sm font-bold text-[#0b1f33]">{sample.query}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
                      {sample.source === "safety_probe" ? (
                        <span className="inline-flex items-center gap-1 font-bold text-slate-600">
                          <ShieldAlert size={11} aria-hidden /> Safety probe
                        </span>
                      ) : (
                        <>
                          <span className="font-bold text-slate-600">Evaluation set</span>
                          <OutcomeBadge rank={sample.stored_rank} depth={depth} />
                        </>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </fieldset>

        {selected ? (
          <div className="min-w-0">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">Sample query</p>
              <p className="mt-1 text-lg font-extrabold leading-snug text-[#0b1f33]">“{selected.query}”</p>
              <p className="mt-2 text-sm text-slate-600">{selected.purpose}</p>
              <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Expected reference note</dt>
                  <dd className="font-mono text-[11px] text-slate-800">{selected.expected_doc_ids.length ? selected.expected_doc_ids.join(", ") : "None (behaviour test, not a retrieval test)"}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Stored run result</dt>
                  <dd className="font-bold text-slate-800">{selected.source === "safety_probe" ? "Not part of the stored retrieval run" : selected.stored_rank ? `Rank #${selected.stored_rank}` : `Not in the top ${depth}`}</dd>
                </div>
              </dl>
              <button
                type="button"
                onClick={() => live.run(selected.query)}
                className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-full bg-teal-700 px-5 text-sm font-bold text-white hover:bg-teal-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
              >
                <Play size={15} aria-hidden /> {live.state ? "Run again" : "Run live"}
              </button>
            </div>
            {live.state ? (
              <div className="mt-6">
                <LiveRunView state={live.state} expected={selected.expected_doc_ids} onRetry={() => live.run(selected.query)} />
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function TraceQuery({ depth }: { depth: number }) {
  const [query, setQuery] = useState("");
  const live = useLiveRun(depth);
  const trimmed = query.trim();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (trimmed) live.run(trimmed);
  };

  return (
    <div>
      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex-1 text-xs font-bold text-slate-600">
          Trace a query through the live pipeline
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={MAX_QUERY}
            placeholder="e.g. What are the warning signs of dehydration in children?"
            className="mt-1 block min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal text-slate-900 outline-none focus:border-teal-700 focus:ring-2 focus:ring-teal-700/20"
          />
        </label>
        <button type="submit" disabled={!trimmed} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-teal-700 px-5 text-sm font-bold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-300">
          <Play size={15} aria-hidden /> Run trace
        </button>
      </form>
      <p className="mt-1.5 text-xs text-slate-500">Use a test question, not real patient details. Traces are not saved to any chat.</p>
      {live.state ? (
        <div className="mt-5">
          <p className="mb-3 text-xs text-slate-500">
            Trace for “<span className="font-bold text-slate-700">{live.state.query}</span>”
          </p>
          <LiveRunView state={live.state} expected={[]} onRetry={() => live.state && live.run(live.state.query)} />
        </div>
      ) : null}
    </div>
  );
}
