import type { Citation } from "../../types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-slate-400">Sources</p>
      {citations.map((item, index) => {
        const title = item.title || item.condition || "Medical reference";
        const inner = (
          <>
            <span className="text-xs font-extrabold text-teal-700">[{index + 1}]</span>
            <span className="block text-sm font-bold text-slate-900">{title}</span>
            {item.source ? <span className="text-xs text-slate-500">{item.source}</span> : null}
          </>
        );
        if (item.url) {
          return (
            <a
              key={`${title}-${index}`}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="block rounded-2xl border border-teal-100 px-3 py-2 hover:bg-teal-50"
            >
              {inner}
            </a>
          );
        }
        return (
          <div key={`${title}-${index}`} className="rounded-2xl border border-teal-100 px-3 py-2">
            {inner}
          </div>
        );
      })}
    </div>
  );
}
