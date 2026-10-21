import type { ChatMessage } from "../types";
import { looksEmergency } from "./emergency";

const GREETING =
  /^(hi|hello|hey|yo|hola|howdy|good\s+(morning|afternoon|evening)|thanks?( you)?|thx|ty|ok(ay)?|k+|cool|great|nice|sure|yep|yes|no|nope|bye|goodbye|see you|cheers|please)[.!?]*$/i;
const WELLBEING = /^(i am|i'm|im|i feel)\s+(good|fine|ok|okay|well|great|alright|better)[.!?]*$/i;
const SMALLTALK = /^(how are you|what's up|what is up|who are you|what (can|do) you do|what is (this|mediassist)|help me|test|testing)[.!?]*$/i;
const MEDICAL =
  /\b(pain|ache|aching|hurt|hurts|sore|fever|cough|cold|flu|vomit|nause|dizz|rash|bleed|breath|chest|headache|migraine|stomach|abdomen|throat|symptom|illness|\bill\b|sick|infect|swell|diabet|asthma|covid|pregnan|period|urine|\bpee\b|diarrhea|constipat|anxiety|depress|insomni|allerg|wound|burn|fracture|sprain|doctor|hospital|triage|condition|diagnos|medicine|medication|itchy|itching|fatigue|tired|weak|lump|swelling|runny nose|congestion|wheeze|cramp|bloating|heartburn|reflux|\w+(itis|osis|emia|oma|pathy)|what is|what'?s|tell me about|extra detail:|body map context)\b/i;
const FOLLOWUP = /\b(also|as well|with that|tell me more|more about|second (one|condition|match)|first (one|condition|match)|what about|how about|worse|better|still have)\b/i;

function plainQuery(text: string): string {
  return text
    .replace(/Body map context \(user-described discomfort, not a diagnosis\):[\s\S]*$/i, "")
    .replace(/\n\nExtra detail:[\s\S]*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function looksMedical(text: string, history: ChatMessage[] = []): boolean {
  const raw = text.trim();
  if (!raw) return false;
  if (looksEmergency(raw)) return true;
  if (/body map context/i.test(raw) || /extra detail:/i.test(raw)) return true;
  const plain = plainQuery(raw);
  if (GREETING.test(plain) || WELLBEING.test(plain) || SMALLTALK.test(plain)) return false;
  if (MEDICAL.test(plain)) return true;
  const medicalThread = history.some(
    (item) => item.possible_conditions?.length || item.triage || MEDICAL.test(item.content || ""),
  );
  if (medicalThread && FOLLOWUP.test(plain)) return true;
  return false;
}

export function needsSymptomIntake(text: string, messages: ChatMessage[]): boolean {
  if (looksEmergency(text)) return false;
  if (!looksMedical(text, messages)) return false;
  if (/extra detail:/i.test(text)) return false;
  const medicalThread = messages.some(
    (item) => item.possible_conditions?.length || item.triage || looksMedical(item.content || "", []),
  );
  if (medicalThread) return false;
  return true;
}
