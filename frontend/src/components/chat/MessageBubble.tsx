import { Copy, Stethoscope } from "lucide-react";
import Markdown from "react-markdown";
import type { ChatMessage } from "../../types";
import { useApp } from "../../context/AppContext";
import { TriageBanner } from "../medical/TriageBadge";
import { CitationList } from "./CitationList";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const { toast } = useApp();
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[85%] rounded-3xl rounded-br-md bg-teal-700 px-4 py-3 text-sm leading-6 text-white">
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    );
  }

  return (
    <article className="flex max-w-[min(48rem,100%)] gap-3">
      <span className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-teal-100 text-teal-800">
        <Stethoscope size={16} />
      </span>
      <div className="min-w-0 flex-1 rounded-3xl rounded-tl-md border border-teal-100 bg-white px-4 py-4 shadow-sm">
        {message.streaming && !message.content ? (
          <p className="text-sm font-semibold text-teal-800">Generating...</p>
        ) : (
          <div className="space-y-2 text-sm leading-6 text-slate-700 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_h1]:font-extrabold [&_h2]:font-extrabold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:font-bold [&_a]:text-teal-800 [&_strong]:font-extrabold">
            <Markdown>{message.content || ""}</Markdown>
            {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
          </div>
        )}
        {message.recommendations.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-slate-700">
            {message.recommendations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
        {message.possible_conditions.length ? (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-slate-400">Possible explanations</p>
            {message.possible_conditions.slice(0, 4).map((item, index) => (
              <div key={`${item.condition}-${index}`} className="flex items-center justify-between rounded-xl bg-teal-50 px-3 py-2">
                <span className="text-sm font-bold text-slate-900">
                  {index + 1}. {item.condition}
                </span>
                <span className="text-xs font-extrabold text-teal-800">{Math.round((item.relevance_score || 0) * 100)}%</span>
              </div>
            ))}
          </div>
        ) : null}
        <div className="mt-3">
          <TriageBanner level={message.triage?.level} guidance={message.triage?.guidance} />
        </div>
        <CitationList citations={message.citations} />
        {message.disclaimer ? <p className="mt-3 text-xs leading-5 text-slate-500">{message.disclaimer}</p> : null}
        {!message.streaming && message.content ? (
          <button
            className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-teal-800"
            onClick={() => {
              void navigator.clipboard.writeText(message.content);
              toast("Copied to clipboard.");
            }}
            aria-label="Copy message"
          >
            <Copy size={14} /> Copy
          </button>
        ) : null}
      </div>
    </article>
  );
}
