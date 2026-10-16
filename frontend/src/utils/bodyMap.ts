export type BodyRegion = "head" | "chest" | "abdomen" | "back" | "arm" | "leg";
export type BodyView = "front" | "back";

export const REGION_ORDER: BodyRegion[] = ["head", "chest", "abdomen", "back", "arm", "leg"];

export const REGION_LABELS: Record<BodyRegion, string> = {
  head: "Head",
  chest: "Chest",
  abdomen: "Abdomen",
  back: "Back",
  arm: "Arm",
  leg: "Leg",
};

export const REGION_SYMPTOMS: Record<BodyRegion, string[]> = {
  head: ["Headache", "Dizziness", "Scalp pain", "Sore throat"],
  chest: ["Chest pain", "Cough", "Breathlessness"],
  abdomen: ["Stomach pain", "Nausea", "Vomiting"],
  back: ["Back pain", "Stiffness"],
  arm: ["Arm pain", "Numbness", "Swelling"],
  leg: ["Leg pain", "Swelling", "Numbness"],
};

export const FALLBACK_SYMPTOMS = ["Fever", "Tiredness", "Body ache"];

export const BODY_MAP_DISCLAIMER =
  "The body map only records where you feel discomfort. It is not a diagnosis.";

export function toggleItem<T>(items: T[], item: T): T[] {
  return items.includes(item) ? items.filter((entry) => entry !== item) : [...items, item];
}

export function suggestedSymptoms(regions: BodyRegion[]): string[] {
  if (!regions.length) return [...FALLBACK_SYMPTOMS];
  return unique(regions.flatMap((region) => REGION_SYMPTOMS[region]));
}

export function summarizeSelection(regions: BodyRegion[], symptoms: string[]): string {
  const locationText = regions.map((region) => REGION_LABELS[region]).join(", ");
  const symptomText = symptoms.join(", ");
  if (locationText && symptomText) return `${locationText} · ${symptomText}`;
  if (locationText) return locationText;
  if (symptomText) return symptomText;
  return "No body regions or symptoms selected";
}

export function formatReviewLine(freeText: string, regions: BodyRegion[], symptoms: string[]): string {
  const typed = freeText.trim();
  const hasMap = Boolean(regions.length || symptoms.length);
  const summary = hasMap ? summarizeSelection(regions, symptoms) : "";
  return [summary, typed].filter(Boolean).join(" · ");
}

export function buildBodyMapQuery(freeText: string, regions: BodyRegion[], symptoms: string[]): string {
  const typed = freeText.trim();
  const locationText = unique(regions.map((region) => REGION_LABELS[region])).join(", ");
  const symptomText = unique(symptoms).join(", ");
  const parts: string[] = [];
  if (typed) parts.push(typed);
  if (locationText || symptomText) {
    const details = [
      locationText ? `locations = ${locationText}` : "",
      symptomText ? `symptoms = ${symptomText}` : "",
    ]
      .filter(Boolean)
      .join("; ");
    parts.push(`Body map context (user-described discomfort, not a diagnosis): ${details}.`);
  }
  return parts.join("\n\n").trim();
}

function unique(items: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of items) {
    const key = item.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push(item.trim());
  }
  return result;
}
