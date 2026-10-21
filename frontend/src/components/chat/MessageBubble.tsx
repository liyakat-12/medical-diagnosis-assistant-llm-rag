import { Copy, MapPin, Stethoscope } from "lucide-react";
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

const MARKDOWN_CLASS =
  "break-anywhere space-y-3 text-sm leading-7 text-slate-700 [&_a]:font-bold [&_a]:text-teal-800 [&_h1]:text-lg [&_h1]:font-extrabold [&_h2]:text-base [&_h2]:font-extrabold [&_h3]:text-sm [&_h3]:font-extrabold [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_pre]:overflow-x-auto [&_strong]:font-extrabold [&_ul]:list-disc [&_ul]:pl-5";

function SectionTitle({ children }: { children: string }) {
  return <h3 className="mb-2 text-xs font-extrabold uppercase tracking-[0.14em] text-slate-400">{children}</h3>;
}

function visibleExplanation(content: string): string {
  const cut = content.search(/\n+(?:#{1,3}\s*)?(?:possible matches|recommendations)\s*:/i);
  const text = (cut >= 0 ? content.slice(0, cut) : content).trim();
  if (/^(?:#{1,3}\s*)?(?:possible matches|recommendations)\s*:/i.test(text)) return "";
  return text;
}

function hasMedicalCards(message: ChatMessage): boolean {
  const level = message.triage?.level;
  return Boolean(
    message.possible_conditions.length ||
      message.citations.length ||
      (level && level !== "none"),
  );
}

function ThinkingIndicator({ status }: { status?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white px-4 py-3 ring-1 ring-teal-100" aria-live="polite">
      <span className="flex gap-1" aria-hidden>
        {[0, 1, 2].map((index) => (
          <span
            key={index}
            className="h-2 w-2 animate-bounce rounded-full bg-teal-600"
            style={{ animationDelay: `${index * 120}ms` }}
          />
        ))}
      </span>
      <p className="text-sm font-semibold text-teal-800">{status || "Understanding your message..."}</p>
    </div>
  );
}

function OutcomeList({ message }: { message: ChatMessage }) {
  const outcomes = withPercents(message.possible_conditions);
  if (message.streaming && !outcomes.length) {
    return (
      <ul className="space-y-2">
        {[0, 1, 2, 3].map((index) => (
          <li key={index} className="h-10 animate-pulse rounded-xl bg-teal-50" />
        ))}
      </ul>
    );
  }
  if (!outcomes.length) return null;
  return (
    <ul className="space-y-2">
      {outcomes.map((item) => {
        const percent = item.match_percent || 0;
        return (
          <li key={`${item.condition}-${item.title}`} className="rounded-xl bg-teal-50/80 px-3 py-2.5">
            <div className="flex items-center justify-between gap-3">
              <span className="min-w-0 break-anywhere text-sm font-bold text-slate-900">{formatConditionName(item.condition)}</span>
              <span className="shrink-0 text-xs font-extrabold text-teal-800" title="Share of retrieved-match scores, not a diagnosis probability">
                {percent}% match
              </span>
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

function UrgencyList({
  message,
  onOpenHospitals,
}: {
  message: ChatMessage;
  onOpenHospitals?: () => void;
}) {
  const triage = message.triage;
  if (message.streaming && !triage) {
    return <p className="text-sm font-semibold text-slate-500">Checking urgency...</p>;
  }
  if (!triage || triage.level === "none") return null;
  return (
    <div
      className={cn(
        "rounded-xl px-4 py-3",
        triage.level === "emergency" && "bg-red-600 text-white",
        triage.level === "consult_doctor" && "bg-amber-100 text-amber-950",
        triage.level === "self_care" && "bg-emerald-50 text-emerald-950",
      )}
      role={triage.level === "emergency" ? "alert" : undefined}
    >
      <p className="text-sm font-extrabold">{triage.label}</p>
      <p className="mt-1 text-sm leading-6">{triage.guidance || URGENCY_COPY[triage.level]}</p>
      {triage.level === "emergency" ? (
        <div className="mt-3 flex flex-wrap gap-2">
          <a href={EMERGENCY_TEL} className="inline-flex min-h-11 items-center rounded-full bg-white px-3 text-sm font-extrabold text-red-700">
            Call {EMERGENCY_NUMBER} now
          </a>
          {onOpenHospitals ? (
            <button
              type="button"
              onClick={onOpenHospitals}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-white/70 px-3 text-sm font-extrabold text-white hover:bg-red-500"
            >
              <MapPin size={14} /> Emergency — View Nearby Hospitals
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function CitationBullets({ message }: { message: ChatMessage }) {
  const citations = uniqueCitations(message).filter((item) => item.title || item.condition || item.source);
  if (message.streaming && !citations.length) {
    return <p className="text-sm font-semibold text-slate-500">Collecting sources...</p>;
  }
  if (!citations.length) return null;
  return (
    <ol className="space-y-2">
      {citations.map((item, index) => {
        const title = item.title || formatConditionName(item.condition);
        const inner = (
          <>
            <span className="font-extrabold text-teal-800">{index + 1}.</span> {title}
            {item.source ? <span className="text-slate-500"> — {item.source}</span> : null}
          </>
        );
        return (
          <li key={`${title}-${index}`} className="break-anywhere text-sm leading-6 text-slate-700">
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer" className="font-semibold hover:text-teal-800">
                {inner}
              </a>
            ) : (
              inner
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function MessageBubble({
  message,
  status,
  onOpenHospitals,
}: {
  message: ChatMessage;
  status?: string;
  onOpenHospitals?: () => void;
}) {
  const { toast } = useApp();
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-[min(32rem,92%)] rounded-2xl rounded-br-md bg-sky-700 px-4 py-3 text-sm leading-6 text-white">
        <p className="whitespace-pre-wrap break-anywhere">{message.content}</p>
      </div>
    );
  }

  const structured = hasMedicalCards(message);
  const explanation = visibleExplanation(message.content || "");
  const showFallback = message.refused || (!structured && Boolean(message.content));
  const showThinking = message.streaming && !structured && !message.content;
  const recommendations = message.recommendations.filter((item) => item.trim());
  const showTriage = Boolean(message.triage && message.triage.level !== "none") || (message.streaming && structured);

  return (
    <article className="flex max-w-full gap-3">
      <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-sky-100 text-sky-800">
        <Stethoscope size={14} />
      </span>
      <div className="min-w-0 flex-1">
        {showThinking ? <ThinkingIndicator status={status} /> : null}
        {showFallback ? (
          <div className={MARKDOWN_CLASS}>
            <Markdown>{message.content || ""}</Markdown>
            {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
          </div>
        ) : (
          <div className="space-y-5">
            {showTriage ? (
              <section>
                <SectionTitle>Urgency</SectionTitle>
                <UrgencyList message={message} onOpenHospitals={onOpenHospitals} />
              </section>
            ) : null}
            {recommendations.length ? (
              <section>
                <SectionTitle>Recommendations</SectionTitle>
                <ul className="list-disc space-y-1 rounded-xl bg-white px-5 py-3 pl-8 text-sm leading-6 text-slate-800 ring-1 ring-teal-100">
                  {recommendations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ) : null}
            {explanation ? (
              <section className={MARKDOWN_CLASS}>
                <SectionTitle>Explanation</SectionTitle>
                <Markdown>{explanation}</Markdown>
                {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
              </section>
            ) : null}
            {message.possible_conditions.length || (message.streaming && structured) ? (
              <section>
                <SectionTitle>Possible matches</SectionTitle>
                <OutcomeList message={message} />
                {message.possible_conditions.length ? (
                  <p className="mt-2 text-xs text-slate-500">Percentages show how the retrieved notes compare, not the chance of a diagnosis.</p>
                ) : null}
              </section>
            ) : null}
            {message.citations.length || (message.streaming && structured) ? (
              <section>
                <SectionTitle>Sources</SectionTitle>
                <CitationBullets message={message} />
              </section>
            ) : null}
          </div>
        )}
        {!message.streaming && (structured || message.content) ? (
          <button
            className="mt-3 inline-flex min-h-11 items-center gap-1 text-xs font-bold text-slate-500 hover:text-teal-800"
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
