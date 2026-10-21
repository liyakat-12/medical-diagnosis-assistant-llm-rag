import type { TriageLevel } from "../../types";
import { cn } from "../../lib/cn";

const LABELS: Record<Exclude<TriageLevel, "none">, string> = {
  self_care: "Self care",
  consult_doctor: "Consult a doctor",
  emergency: "Emergency",
};

const COPY: Record<Exclude<TriageLevel, "none">, string> = {
  self_care: "Monitor your symptoms and consider general self-care.",
  consult_doctor: "Consider speaking with a healthcare professional.",
  emergency: "Seek immediate medical attention.",
};

export function TriageBadge({ level }: { level?: TriageLevel | null }) {
  if (!level || level === "none") return null;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-extrabold uppercase tracking-wide",
        level === "emergency" && "bg-red-600 text-white",
        level === "consult_doctor" && "bg-yellow-400 text-yellow-950",
        level === "self_care" && "bg-green-600 text-white",
      )}
    >
      {LABELS[level]}
    </span>
  );
}

export function TriageBanner({ level, guidance }: { level?: TriageLevel | null; guidance?: string }) {
  if (!level || level === "none") return null;
  return (
    <div
      role="status"
      className={cn(
        "rounded-2xl border-2 px-4 py-3",
        level === "emergency" && "border-red-700 bg-red-600 text-white",
        level === "consult_doctor" && "border-yellow-500 bg-yellow-400 text-yellow-950",
        level === "self_care" && "border-green-700 bg-green-600 text-white",
      )}
    >
      <p className="text-sm font-extrabold uppercase tracking-wide">{LABELS[level]}</p>
      <p className="mt-1 text-sm font-semibold leading-6">{guidance || COPY[level]}</p>
    </div>
  );
}
