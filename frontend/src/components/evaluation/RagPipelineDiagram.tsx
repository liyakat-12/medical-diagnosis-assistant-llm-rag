import { ChevronDown, ChevronRight, FileText, Filter, MessageSquareText, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";

const STAGES = [
  { label: "User Query", icon: MessageSquareText },
  { label: "Query Preparation", icon: SlidersHorizontal },
  { label: "Vector Retrieval", icon: Search },
  { label: "Evidence Selection", icon: Filter },
  { label: "Answer Generation", icon: FileText },
  { label: "Citation and Safety Checks", icon: ShieldCheck },
] as const;

/** Design reference only. It does not report whether a stage ran. */
export function RagPipelineDiagram() {
  return (
    <figure>
      <figcaption className="sr-only">How a question moves through MediAssist. This is the design, not a live run.</figcaption>
      <ol className="flex list-none flex-col gap-2 p-0 md:flex-row md:items-stretch" aria-label="MediAssist question flow. Design reference only, not a live run.">
        {STAGES.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <li key={stage.label} className="flex flex-1 flex-col items-stretch gap-2 md:flex-row md:items-center">
              <div className="flex min-h-16 flex-1 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-3 md:flex-col md:justify-center md:gap-2 md:px-2 md:text-center">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#e7f3f1] text-teal-800">
                  <Icon size={16} aria-hidden />
                </span>
                <span className="text-sm font-bold leading-5 text-[#0b1f33]">{stage.label}</span>
              </div>
              {index < STAGES.length - 1 ? (
                <span aria-hidden className="flex justify-center text-slate-300">
                  <ChevronDown className="md:hidden" size={16} />
                  <ChevronRight className="hidden md:block" size={16} />
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-xs text-slate-500">This describes the design. It is not a live run.</p>
    </figure>
  );
}
