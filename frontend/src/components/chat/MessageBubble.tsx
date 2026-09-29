import { Copy, Stethoscope } from "lucide-react";
import Markdown from "react-markdown";
import type { ChatMessage } from "../../types";
import { useApp } from "../../context/AppContext";
import { cn } from "../../lib/cn";
import { formatAssistantCopy, formatConditionName, uniqueCitations, withPercents } from "../../utils/report";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";

const URGENCY_COPY: Record<string, string> = {
  self_care: "This looks suitable for home monitoring unless it gets worse.",
  consult_doctor: "Book a clinician visit soon so this can be checked properly.",
  emergency: "This may be urgent. Seek emergency care now.",
};

function ReportHeading({ step, title }: { step: string; title: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="grid h-6 w-6 place-items-center rounded-full bg-teal-700 text-[11px] font-extrabold text-white">
        {step}
      </span>
      <h3 className="text-sm font-extrabold text-slate-900">{title}</h3>
    </div>
  );
}

function OutcomeList({ message }: { message: ChatMessage }) {
  const outcomes = withPercents(message.possible_conditions);
  if (message.streaming && !outcomes.length) {
    return (
      <ul className="space-y-2">
        {[0, 1, 2, 3].map((index) => (
          <li key={index} className="h-11 animate-pulse rounded-2xl bg-teal-50" />
        ))}
      </ul>
    );
  }
  if (!outcomes.length) {
    return <p className="text-sm leading-6 text-slate-600">• No close matches yet. Add a bit more detail about your symptoms.</p>;
  }
  return (
    <ul className="space-y-2">
      {outcomes.map((item) => {
        const percent = item.match_percent || 0;
        return (
          <li key={`${item.condition}-${item.title}`} className="rounded-2xl bg-teal-50/80 px-3 py-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-bold text-slate-900">• {formatConditionName(item.condition)}</span>
              <span className="shrink-0 text-sm font-extrabold text-teal-800">{percent}%</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
              <div className="h-full rounded-full bg-teal-600" style={{ width: `${Math.max(percent, 4)}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function UrgencyList({ message }: { message: ChatMessage }) {
  const triage = message.triage;
  if (message.streaming && !triage) {
    return <p className="text-sm font-semibold text-slate-500">Checking urgency...</p>;
  }
  if (!triage) {
    return <p className="text-sm leading-6 text-slate-600">• Urgency will appear after the notes are checked.</p>;
  }
  return (
    <div
      className={cn(
        "rounded-2xl px-4 py-3",
        triage.level === "emergency" && "bg-red-600 text-white",
        triage.level === "consult_doctor" && "bg-amber-300 text-amber-950",
        triage.level === "self_care" && "bg-emerald-600 text-white",
      )}
    >
      <ul className="space-y-1.5 text-sm leading-6">
        <li className="font-extrabold">• {triage.label}</li>
        <li>• {triage.guidance || URGENCY_COPY[triage.level]}</li>
        {triage.level === "emergency" ? (
          <li>
            •{" "}
            <a href={EMERGENCY_TEL} className="underline">
              Call {EMERGENCY_NUMBER} now
            </a>
          </li>
        ) : null}
      </ul>
    </div>
  );
}

function CitationBullets({ message }: { message: ChatMessage }) {
  const citations = uniqueCitations(message);
  if (message.streaming && !citations.length) {
    return <p className="text-sm font-semibold text-slate-500">Collecting sources...</p>;
  }
  if (!citations.length) {
    return <p className="text-sm leading-6 text-slate-600">• No sources retrieved for this reply.</p>;
  }
  return (
    <ul className="space-y-2">
      {citations.map((item, index) => {
        const title = item.title || formatConditionName(item.condition);
        const body = (
          <>
            <span className="font-extrabold text-teal-800">[{index + 1}]</span> {title}
            {item.source ? <span className="text-slate-500"> — {item.source}</span> : null}
          </>
        );
        return (
          <li key={`${title}-${index}`} className="text-sm leading-6 text-slate-700">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-teal-800">
                • {body}
              </a>
            ) : (
              <span>• {body}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const { toast } = useApp();
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[min(36rem,85%)] rounded-3xl rounded-br-md bg-teal-700 px-4 py-3 text-sm leading-6 text-white shadow-sm">
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    );
  }

  const structured = Boolean(message.possible_conditions.length || message.triage || message.citations.length);
  const showFallback = message.refused || (!message.streaming && !structured && Boolean(message.content));

  return (
    <article className="flex max-w-[min(48rem,100%)] gap-3">
      <span className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-teal-100 text-teal-800 shadow-sm">
        <Stethoscope size={16} />
      </span>
      <div className="min-w-0 flex-1 rounded-3xl rounded-tl-md border border-teal-100 bg-white px-4 py-4 shadow-sm">
        {showFallback ? (
          <div className="space-y-2 text-sm leading-6 text-slate-700 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:font-bold [&_a]:text-teal-800 [&_strong]:font-extrabold">
            <Markdown>{message.content || ""}</Markdown>
            {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
          </div>
        ) : (
          <div className="space-y-5">
            <section>
              <ReportHeading step="1" title="Possible outcomes" />
              <OutcomeList message={message} />
            </section>
            <section>
              <ReportHeading step="2" title="Urgency" />
              <UrgencyList message={message} />
            </section>
            <section>
              <ReportHeading step="3" title="Citations" />
              <CitationBullets message={message} />
            </section>
          </div>
        )}
        {message.disclaimer && (structured || !message.streaming) ? (
          <p className="mt-4 text-xs leading-5 text-slate-500">{message.disclaimer}</p>
        ) : null}
        {!message.streaming && (structured || message.content) ? (
          <button
            className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-teal-800"
            onClick={() => {
              void navigator.clipboard.writeText(formatAssistantCopy(message));
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
