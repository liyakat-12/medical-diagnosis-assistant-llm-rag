const EMERGENCY_HINT =
  /chest pain|crushing|can'?t breathe|cannot breathe|struggling to breathe|turning blue|slurred speech|face droop|suicid|want to die|kill myself|anaphyla|stroke|heart attack|overdose|seizure|unconscious|vomiting blood/i;

/** India national emergency number (also routes ambulance services). */
export const EMERGENCY_NUMBER = "112";
export const EMERGENCY_TEL = `tel:${EMERGENCY_NUMBER}`;

export function looksEmergency(text: string): boolean {
  return EMERGENCY_HINT.test(text);
}
