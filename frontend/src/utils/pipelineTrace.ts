import type { PipelineRun } from "../types/evaluation";

export type StageId = "safety" | "prepare" | "retrieve" | "select" | "generate" | "verify";
export type StageStatus = "ran" | "skipped" | "stopped";

export type PipelineStage = {
  id: StageId;
  title: string;
  purpose: string;
  timingKey?: "classify_ms" | "retrieve_ms" | "generate_ms";
};

export const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: "safety",
    title: "Safety pre-check",
    purpose: "Rule-based checks refuse prescription and dosage requests before anything else runs.",
  },
  {
    id: "prepare",
    title: "Query preparation",
    purpose: "Classifies the message, keeps relevant conversation context, and normalises wording for search.",
    timingKey: "classify_ms",
  },
  {
    id: "retrieve",
    title: "Vector retrieval",
    purpose: "Embeds the prepared query, searches the Chroma index, and re-ranks candidates with a cross-encoder.",
    timingKey: "retrieve_ms",
  },
  {
    id: "select",
    title: "Evidence selection",
    purpose: "Keeps passages that clear the relevance thresholds. Weak matches are not used as evidence.",
  },
  {
    id: "generate",
    title: "Answer generation",
    purpose: "Writes the reply from the selected passages only, or a cautious fallback when evidence is weak.",
    timingKey: "generate_ms",
  },
  {
    id: "verify",
    title: "Citations and safety",
    purpose: "Attaches sources, audits whether claims are cited, and applies emergency triage rules.",
  },
];

export type StageTrace = {
  stage: PipelineStage;
  status: StageStatus;
  ms: number | null;
  detail: string;
};

function timing(run: PipelineRun, key?: PipelineStage["timingKey"]): number | null {
  if (!key) return null;
  const value = run.timings?.[key];
  return typeof value === "number" && value > 0 ? value : null;
}

export function tracePipeline(run: PipelineRun): StageTrace[] {
  const refused = run.refused;
  const retrieved = timing(run, "retrieve_ms") !== null;
  const generated = timing(run, "generate_ms") !== null;
  const cited = run.citations?.length ?? 0;
  const grounded = run.evidence_origin === "knowledge_base" || run.evidence_origin === "mixed";

  return PIPELINE_STAGES.map((stage): StageTrace => {
    const ms = timing(run, stage.timingKey);
    switch (stage.id) {
      case "safety":
        return refused
          ? { stage, status: "stopped", ms: null, detail: "The request was refused here; later stages did not run." }
          : { stage, status: "ran", ms: null, detail: "No prescription or dosage request detected. Not separately timed." };
      case "prepare":
        if (refused) return { stage, status: "skipped", ms: null, detail: "Not reached." };
        return { stage, status: ms !== null ? "ran" : "skipped", ms, detail: run.question_type ? `Question type: ${run.question_type.replace(/_/g, " ").toLowerCase()}.` : "Classified the message." };
      case "retrieve":
        if (!retrieved) return { stage, status: "skipped", ms: null, detail: refused ? "Not reached." : "Not run for this message (for example, a non-medical message)." };
        return { stage, status: "ran", ms, detail: "Searched the knowledge-base index." };
      case "select":
        if (!retrieved) return { stage, status: "skipped", ms: null, detail: "No retrieved passages to select from." };
        return {
          stage,
          status: "ran",
          ms: null,
          detail: grounded ? `${cited} cited source${cited === 1 ? "" : "s"} kept as evidence. Timed with retrieval.` : "No passage was strong enough to use as evidence. Timed with retrieval.",
        };
      case "generate":
        if (!generated) return { stage, status: "skipped", ms: null, detail: refused ? "A fixed refusal message was returned instead." : "A fixed rule-based reply was returned instead." };
        return { stage, status: "ran", ms, detail: grounded ? "Reply written from the selected passages." : "Reply written without knowledge-base evidence." };
      case "verify": {
        if (refused) return { stage, status: "skipped", ms: null, detail: "Not reached." };
        if (!retrieved) return { stage, status: "skipped", ms: null, detail: "No retrieved evidence, so there was nothing to cite or audit." };
        const audited = run.faithfulness ? "Citation audit ran." : "No citation audit (no evidence was used).";
        const triage = run.triage?.label ? ` Triage: ${run.triage.label}.` : "";
        return { stage, status: "ran", ms: null, detail: `${audited}${triage} Not separately timed.` };
      }
    }
  });
}
