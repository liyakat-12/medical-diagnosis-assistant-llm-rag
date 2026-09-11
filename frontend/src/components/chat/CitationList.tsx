import type { Citation } from "../../types";
import { formatConditionName } from "../../utils/report";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <ul className="mt-3 space-y-2">
      {citations.map((item, index) => {
        const title = item.title || formatConditionName(item.condition) || "Medical reference";
        const body = (
          <>
            <span className="font-extrabold text-teal-800">[{index + 1}]</span> {title}
            {item.source ? <span className="text-slate-500"> — {item.source}</span> : null}
          </>
        );
        if (item.url) {
          return (
            <li key={`${title}-${index}`} className="text-sm leading-6">
              <a href={item.url} target="_blank" rel="noreferrer" className="font-semibold text-slate-800 hover:text-teal-800">
                • {body}
              </a>
            </li>
          );
        }
        return (
          <li key={`${title}-${index}`} className="text-sm leading-6 text-slate-700">
            • {body}
          </li>
        );
      })}
    </ul>
  );
}
