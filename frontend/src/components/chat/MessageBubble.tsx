import { memo, type ReactNode } from "react";
import { Copy, MapPin, Stethoscope } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, Citation } from "../../types";
import { useApp } from "../../context/AppContext";
import { cn } from "../../lib/cn";
import { normalizeMarkdownTables } from "../../utils/markdown";
import { isIncompleteMessage } from "../../utils/chatSession";
import { evidenceStatusItems, formatAssistantCopy, formatConditionName, isSymptomCardMessage, retrievedCitations, withPercents } from "../../utils/report";
import { EMERGENCY_NUMBER, EMERGENCY_TEL } from "../../utils/emergency";

const URGENCY_COPY: Record<string, string> = {
  self_care: "This looks suitable for home monitoring unless it gets worse.",
  consult_doctor: "Book a clinician visit soon so this can be checked properly.",
  emergency: "This may be urgent. Seek emergency care now.",
};

const MARKDOWN_CLASS =
  "break-anywhere space-y-3 text-sm leading-7 text-slate-700 [&_a]:font-bold [&_a]:text-teal-800 [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:font-mono [&_h1]:text-lg [&_h1]:font-extrabold [&_h2]:text-base [&_h2]:font-extrabold [&_h3]:text-sm [&_h3]:font-extrabold [&_li]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-slate-900 [&_pre]:p-3 [&_pre]:text-slate-100 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_strong]:font-extrabold [&_ul]:list-disc [&_ul]:pl-5";

const MARKDOWN_COMPONENTS = {
  table: ({ children }: { children?: ReactNode }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full min-w-[20rem] border-collapse text-left text-sm">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="border border-slate-200 bg-slate-50 px-2 py-1 font-extrabold">{children}</th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="border border-slate-200 px-2 py-1 align-top">{children}</td>
  ),
};

function MarkdownBody({ children }: { children: string }) {
  return (
    <div className={MARKDOWN_CLASS}>
      <Markdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
        {normalizeMarkdownTables(children)}
      </Markdown>
    </div>
  );
}

function evidenceCaption(origin: unknown, citations: Citation[] = []): string {
  const raw = String(origin || "");
  const cites = citations.map((item) => `${item.title || ""} ${item.source || ""}`).join(" ");
  const general = /not verified|General AI medical knowledge|No matching sources/i.test(cites);
  if (raw === "llm" || (general && raw !== "knowledge_base" && raw !== "mixed")) {
    return "This explanation is general medical information. It was not retrieved from the MediAssist knowledge base and has not been verified against those notes.";
  }
  if (raw === "mixed") {
    return "Some of this explanation is from retrieved knowledge-base notes; other parts are general medical knowledge and are not verified against those notes.";
  }
  if (raw === "knowledge_base") {
    return "This explanation is based on retrieved MediAssist knowledge-base notes. Citations are listed below when available.";
  }
  return "";
}

function EvidenceNote({ message }: { message: ChatMessage }) {
  if (evidenceStatusItems(message).length) return null;
  const caption = evidenceCaption(message.metadata?.evidence_origin, message.citations);
  if (!caption) return null;
  return <p className="mt-3 text-xs leading-5 text-slate-500">{caption}</p>;
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="mb-2 text-xs font-extrabold uppercase tracking-[0.14em] text-slate-400">{children}</h3>;
}

function visibleExplanation(content: string): string {
  const cut = content.search(/\n+(?:#{1,3}\s*)?(?:possible matches|recommendations)\s*:/i);
  const text = (cut >= 0 ? content.slice(0, cut) : content).trim();
  if (/^(?:#{1,3}\s*)?(?:possible matches|recommendations)\s*:/i.test(text)) return "";
  return text;
}

function isReferenceEducation(message: ChatMessage): boolean {
  if (message.triage?.level === "emergency") return false;
  const questionType = String(message.metadata?.question_type || "");
  const personal = message.metadata?.personal_context === true;
  if (["MEDICAL_EDUCATION", "TREATMENT_INFORMATION", "MEDICATION_SAFETY"].includes(questionType)) {
    return true;
  }
  return !personal && ["SYMPTOM_INFORMATION", "POSSIBLE_CAUSES", "FOLLOW_UP"].includes(questionType);
}

function hasMedicalCards(message: ChatMessage): boolean {
  return isSymptomCardMessage(message) && !isReferenceEducation(message);
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
              <span className="shrink-0 text-xs font-extrabold text-teal-800" title="Retrieval-match share among listed notes, not a diagnosis probability">
                {percent}% retrieval match
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
  const citations = retrievedCitations(message);
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

function EvidenceStatusList({ message }: { message: ChatMessage }) {
  const items = evidenceStatusItems(message);
  if (!items.length) return null;
  return (
    <ul className="space-y-1.5 text-sm leading-6 text-slate-600">
      {items.map((item, index) => {
        const title = item.title || formatConditionName(item.condition);
        return (
          <li key={`${title}-${index}`} className="break-anywhere">
            {title}
            {item.source ? <span className="text-slate-500"> — {item.source}</span> : null}
          </li>
        );
      })}
    </ul>
  );
}

function EvidenceSections({ message }: { message: ChatMessage }) {
  const retrieved = retrievedCitations(message);
  const statusItems = evidenceStatusItems(message);
  if (message.streaming && !retrieved.length && !statusItems.length) {
    return (
      <section className="mt-5">
        <SectionTitle>Sources</SectionTitle>
        <p className="text-sm font-semibold text-slate-500">Collecting sources...</p>
      </section>
    );
  }
  return (
    <>
      {retrieved.length ? (
        <section className="mt-5">
          <SectionTitle>Sources</SectionTitle>
          <CitationBullets message={message} />
          {message.faithfulness && typeof message.faithfulness.summary === "string" ? (
            <p className="mt-2 text-xs text-slate-500">Citation check: {String(message.faithfulness.summary)}</p>
          ) : null}
        </section>
      ) : null}
      {statusItems.length ? (
        <section className="mt-5">
          <SectionTitle>Evidence status</SectionTitle>
          <EvidenceStatusList message={message} />
        </section>
      ) : null}
    </>
  );
}

export const MessageBubble = memo(function MessageBubble({
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

  const incomplete = isIncompleteMessage(message);
  const reference = isReferenceEducation(message);
  const structured = hasMedicalCards(message) && !incomplete;
  const explanation = visibleExplanation(message.content || "");
  const showFallback = message.refused || incomplete || (!structured && Boolean(message.content));
  const showThinking = message.streaming && !structured && !message.content && !incomplete;
  const recommendations = message.recommendations.filter((item) => item.trim());
  const showTriage = Boolean(message.triage && message.triage.level !== "none") && !reference;
  const showMatches = Boolean(message.possible_conditions.length) && !reference;

  return (
    <article className="flex max-w-full gap-3">
      <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-sky-100 text-sky-800">
        <Stethoscope size={14} />
      </span>
      <div className="min-w-0 flex-1">
        {showThinking ? <ThinkingIndicator status={status} /> : null}
        {showFallback ? (
          <div>
            <MarkdownBody>{message.content || ""}</MarkdownBody>
            {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
            {message.streaming ? null : <EvidenceNote message={message} />}
            {message.streaming ? null : <EvidenceSections message={message} />}
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
              <section>
                <SectionTitle>Explanation</SectionTitle>
                <MarkdownBody>{explanation}</MarkdownBody>
                {message.streaming ? <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-teal-700 align-middle" aria-hidden /> : null}
                {message.streaming ? null : <EvidenceNote message={message} />}
              </section>
            ) : null}
            {showMatches ? (
              <section>
                <SectionTitle>Possible matches</SectionTitle>
                <OutcomeList message={message} />
                {message.possible_conditions.length ? (
                  <p className="mt-2 text-xs text-slate-500">
                    {(message.metadata?.evidence_origin === "llm" ||
                    message.metadata?.evidence_origin === "mixed" ||
                    message.citations.some((item) =>
                      /not verified|General AI medical knowledge|not in local notes/i.test(
                        `${item.source || ""} ${item.title || ""}`,
                      ),
                    ))
                      ? "These matches come from MediAssist general medical knowledge because no close local note was found. Percentages are retrieval-match shares, not a diagnosis chance."
                      : "Percentages are retrieval-match shares among these notes, not the chance of a diagnosis."}
                  </p>
                ) : null}
              </section>
            ) : null}
            {message.citations.length || (message.streaming && structured) ? <EvidenceSections message={message} /> : null}
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
});
