export type BodyRegion =
  | "head"
  | "neck"
  | "chest"
  | "abdomen"
  | "upper_back"
  | "lower_back"
  | "shoulder"
  | "arm"
  | "elbow"
  | "wrist_hand"
  | "hip"
  | "thigh"
  | "knee"
  | "lower_leg"
  | "ankle_foot"
  | "back"
  | "leg";
export type BodyView = "front" | "back";

export const REGION_ORDER: BodyRegion[] = [
  "head",
  "neck",
  "shoulder",
  "chest",
  "abdomen",
  "upper_back",
  "lower_back",
  "arm",
  "elbow",
  "wrist_hand",
  "hip",
  "thigh",
  "knee",
  "lower_leg",
  "ankle_foot",
];

export const REGION_LABELS: Record<BodyRegion, string> = {
  head: "Head",
  neck: "Neck",
  chest: "Chest",
  abdomen: "Abdomen",
  upper_back: "Upper back",
  lower_back: "Lower back",
  shoulder: "Shoulder",
  arm: "Arm",
  elbow: "Elbow",
  wrist_hand: "Wrist and hand",
  hip: "Hip",
  thigh: "Thigh",
  knee: "Knee",
  lower_leg: "Lower leg",
  ankle_foot: "Ankle and foot",
  back: "Back",
  leg: "Leg",
};

export const REGION_DESCRIPTIONS: Record<BodyRegion, string> = {
  head: "Head and face",
  neck: "Neck and throat area",
  chest: "Chest, front of the rib cage",
  abdomen: "Abdomen, stomach area",
  upper_back: "Upper back, between the shoulder blades",
  lower_back: "Lower back, above the hips",
  shoulder: "Shoulder joint",
  arm: "Upper arm and forearm",
  elbow: "Elbow joint",
  wrist_hand: "Wrist, hand, and fingers",
  hip: "Hips, groin, and buttocks",
  thigh: "Thigh",
  knee: "Knee joint",
  lower_leg: "Shin and calf",
  ankle_foot: "Ankle, heel, and foot",
  back: "Back",
  leg: "Leg",
};

export const REGION_GROUPS: { label: string; regions: BodyRegion[] }[] = [
  { label: "Head and neck", regions: ["head", "neck"] },
  { label: "Torso", regions: ["chest", "abdomen", "upper_back", "lower_back", "hip"] },
  { label: "Arms and hands", regions: ["shoulder", "arm", "elbow", "wrist_hand"] },
  { label: "Legs and feet", regions: ["thigh", "knee", "lower_leg", "ankle_foot"] },
];

const VIEW_ONLY: Partial<Record<BodyRegion, BodyView>> = {
  chest: "front",
  abdomen: "front",
  upper_back: "back",
  lower_back: "back",
};

export const REGION_SYMPTOMS: Record<BodyRegion, string[]> = {
  head: ["Headache", "Dizziness", "Scalp pain", "Sore throat"],
  neck: ["Neck pain", "Stiff neck", "Swollen glands"],
  chest: ["Chest pain", "Cough", "Breathlessness"],
  abdomen: ["Stomach pain", "Nausea", "Vomiting"],
  upper_back: ["Upper back pain", "Stiffness"],
  lower_back: ["Lower back pain", "Stiffness", "Pain down the leg"],
  shoulder: ["Shoulder pain", "Stiffness", "Pain lifting the arm"],
  arm: ["Arm pain", "Numbness", "Swelling"],
  elbow: ["Elbow pain", "Swelling"],
  wrist_hand: ["Wrist pain", "Hand numbness", "Tingling fingers", "Swelling"],
  hip: ["Hip pain", "Groin pain", "Stiffness"],
  thigh: ["Thigh pain", "Muscle cramp"],
  knee: ["Knee pain", "Swelling", "Pain on stairs", "Stiffness"],
  lower_leg: ["Calf pain", "Swelling", "Cramp"],
  ankle_foot: ["Ankle pain", "Heel pain", "Swollen ankle"],
  back: ["Back pain", "Stiffness"],
  leg: ["Leg pain", "Swelling", "Numbness"],
};

export const FALLBACK_SYMPTOMS = ["Fever", "Tiredness", "Body ache"];

export const BODY_MAP_DISCLAIMER =
  "The body map only records where you feel discomfort. It is not a diagnosis.";

export function toggleItem<T>(items: T[], item: T): T[] {
  return items.includes(item) ? items.filter((entry) => entry !== item) : [...items, item];
}

export function regionView(region: BodyRegion): BodyView | "both" {
  return VIEW_ONLY[region] ?? "both";
}

export function regionsForView(view: BodyView): BodyRegion[] {
  return REGION_ORDER.filter((region) => {
    const only = regionView(region);
    return only === "both" || only === view;
  });
}

export const VIEW_LABELS: Record<BodyView, string> = { front: "Front View", back: "Back View" };

/** View to show after picking a region from the list: stay put unless the region is drawn only on the other side. */
export function viewForRegion(region: BodyRegion, current: BodyView): BodyView {
  const only = regionView(region);
  return only === "both" ? current : only;
}

export function hiddenInView(regions: BodyRegion[], view: BodyView): BodyRegion[] {
  const visible = new Set(regionsForView(view));
  return regions.filter((region) => !visible.has(region));
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
  const locationLabels = unique(regions.map((region) => REGION_LABELS[region]));
  const symptomList = unique(symptoms);
  const locationText = locationLabels.join(", ");
  const symptomText = symptomList.join(", ");
  const parts: string[] = [];
  // Natural-language line first so embeddings match clinical notes; metadata kept for audit.
  // Keep free text first when present so the user's own words stay primary.
  const naturalBits = unique([
    typed,
    ...symptomList,
    ...locationLabels.map((label) => `${label} discomfort`),
  ]);
  if (naturalBits.length) {
    parts.push(naturalBits.join("; "));
  }
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

export type BodyMapMessage = { content: string; body_regions: BodyRegion[] };

export function buildMessagePayload(freeText: string, regions: BodyRegion[], symptoms: string[]): BodyMapMessage {
  return {
    content: buildBodyMapQuery(freeText, regions, symptoms),
    body_regions: Array.from(new Set(regions)),
  };
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
