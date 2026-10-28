const EMERGENCY_HINT =
  /chest pain|pain in (my )?chest|pressure (in|on) (my )?(the )?chest|chest tightness|crushing|can'?t breathe|cannot breathe|can't catch (my )?breath|struggling to breathe|short(ness)? of breath|turning blue|slurred speech|face droop|suicid|want to die|kill myself|anaphyla|stroke|heart attack|overdose|seizure|unconscious|vomiting blood|thunderclap headache/i;
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

export function looksEmergency(text: string, history: { role?: string; content?: string }[] = []): boolean {
  const match = EMERGENCY_HINT.exec(text);
  if (match && match.index != null) {
    const window = text.slice(Math.max(0, match.index - 48), match.index);
    if (!NEGATION_PREFIX.test(window)) {
      const quoted = (text.slice(0, match.index).match(/"/g) || []).length % 2 === 1;
      if (!(quoted && HYPOTHETICAL.test(text)) && !(HYPOTHETICAL.test(window) && !/\bi (have|am having|got)\b/i.test(text))) {
        return true;
      }
    }
  }
  if (!BREATHLESS_NOW.test(text) || !history.length) return false;
  const prior = history
    .filter((item) => item.role === "user")
    .map((item) => item.content || "")
    .join(" ");
  return CALF_SWELLING.test(prior) && LONG_TRAVEL.test(prior);
}
