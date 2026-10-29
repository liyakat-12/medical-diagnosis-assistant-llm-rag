const STRICT_EMERGENCY =
  /crushing|heart attack|can'?t breathe|cannot breathe|can't catch (my )?breath|struggling to breathe|difficulty breathing|short(ness)? of breath|turning blue|slurred speech|face droop|suicid|want to die|kill myself|anaphyla|stroke|seizure|unconscious|vomiting blood|thunderclap headache|sudden (chest|cardiac) (pain|pressure)|pain (radiating|spreading) (to|down)/i;
const CHEST_DISCOMFORT =
  /\b(chest pain|chest ache|chest pressure|chest tightness|chest discomfort|pain in (?:my |the )?chest|pressure (?:in|on) (?:my |the )?chest|tight(?:ness)? in (?:my|the) chest|chest (?:hurts|hurt|is sore|muscles? hurt))\b/i;
const CHEST_WARNING =
  /\b(sweat\w*|faint\w*|collapse|unconscious|breathless|short(?:ness)? of breath|difficulty breathing|can'?t breathe|cannot breathe|gasping|nausea|vomit\w*|jaw|crushing|severe|worst)\b/i;
const HEMOPTYSIS_AMOUNT =
  "(?:(?:a\\s+)?(?:large|huge)\\s+amount\\s+of\\s+|lots?\\s+of\\s+|a\\s+lot\\s+of\\s+|amounts?\\s+of\\s+)?";
const FRANK_HEMOPTYSIS = new RegExp(
  String.raw`\bcough(?:ing)?\s+up\s+${HEMOPTYSIS_AMOUNT}blood\b|\bcoughing\s+blood\b`,
  "i",
);
const HEMOPTYSIS = new RegExp(
  String.raw`\b(cough(?:ing)?\s+up\s+${HEMOPTYSIS_AMOUNT}blood|coughing\s+blood|blood when i cough|blood when coughing|blood in (?:my |the )?(?:cough|sputum|phlegm|mucus)|(?:my )?cough has blood(?: in it)?|(?:persistent )?cough with blood)\b`,
  "i",
);
const HEMOPTYSIS_EMERGENCY =
  /\b(a lot of blood|lots of blood|large amount of blood|severe bleeding|breathless|difficulty breathing|can'?t breathe|cannot breathe|faint\w*|collapse|dizzy|dizziness|chest pain|chest pressure)\b/i;
const SUDDEN_SEVERE_HEADACHE =
  /\b(?:sudden(?:ly)?|thunderclap)\b.{0,40}\b(?:severe|worst|extremely severe|extreme severity)\b.{0,24}\bheadache\b|\bheadache\b.{0,48}\b(?:sudden(?:ly)?|thunderclap)\b.{0,32}\b(?:severe|worst|extreme(?:ly)?\s+severity|extreme severity)\b|\b(?:extremely severe|worst)\b.{0,24}\bheadache\b/i;
const BREATHLESS_NOW =
  /\b(breathless|short(ness)? of breath|can'?t breathe|cannot breathe|difficulty breathing|gasping for air|can'?t catch (my )?breath)\b/i;
const CALF_SWELLING =
  /\b((swollen|painful|swell\w*|pain)\s+(calf|lower leg)|(calf|lower leg)\s+(is |feels )?(swollen|painful|swell\w*|sore))\b/i;
const LONG_TRAVEL = /\b(long[- ]?(flight|haul|drive|bus|train|travel)|after a long flight|after a flight(?!\s+of))\b/i;
const NEGATION_PREFIX = /\b(no|not|never|without|don't|dont|do not|didn't|did not|isn't|is not)\b/i;
const HYPOTHETICAL = /\b(what if|imagine if|hypothetic|for example|in a (movie|story)|what does|meaning of)\b/i;

/** Keep in sync with backend EMERGENCY_NUMBER (India default 112). */
export const EMERGENCY_NUMBER = "112";
export const EMERGENCY_TEL = `tel:${EMERGENCY_NUMBER}`;

function affirmed(pattern: RegExp, text: string): boolean {
  const match = pattern.exec(text);
  if (!match || match.index == null) return false;
  const window = text.slice(Math.max(0, match.index - 48), match.index);
  if (NEGATION_PREFIX.test(window)) return false;
  const quoted = (text.slice(0, match.index).match(/"/g) || []).length % 2 === 1;
  if (quoted && HYPOTHETICAL.test(text)) return false;
  if (HYPOTHETICAL.test(window) && !/\bi (have|am having|got)\b/i.test(text)) return false;
  return true;
}

export function looksEmergency(text: string, history: { role?: string; content?: string }[] = []): boolean {
  if (affirmed(STRICT_EMERGENCY, text) || affirmed(SUDDEN_SEVERE_HEADACHE, text)) return true;
  if (affirmed(CHEST_DISCOMFORT, text) && affirmed(CHEST_WARNING, text)) return true;
  if (affirmed(FRANK_HEMOPTYSIS, text)) return true;
  if (affirmed(HEMOPTYSIS, text) && affirmed(HEMOPTYSIS_EMERGENCY, text)) return true;
  if (!BREATHLESS_NOW.test(text) || !history.length) return false;
  const prior = history
    .filter((item) => item.role === "user")
    .map((item) => item.content || "")
    .join(" ");
  return CALF_SWELLING.test(prior) && LONG_TRAVEL.test(prior);
}

/** Blood with a cough still needs a clinician even when it is not an emergency. */
export function needsPromptAssessment(text: string): boolean {
  return affirmed(HEMOPTYSIS, text) && !looksEmergency(text);
}
