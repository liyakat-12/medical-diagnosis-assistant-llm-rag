import type { ChatMessage } from "../types";
import { looksEmergency } from "./emergency";

/** Presentation helper for the intake modal. The backend classifier decides what can be answered. */

const GREETING =
  /^(hi|hello|hey|yo|hola|howdy|good\s+(morning|afternoon|evening)|thanks?( you)?|thx|ty|ok(ay)?|k+|cool|great|nice|sure|yep|yes|no|nope|bye|goodbye|see you|cheers|please)[.!?]*$/i;
const WELLBEING = /^(i am|i'm|im|i feel)\s+(good|fine|ok|okay|well|great|alright|better)[.!?]*$/i;
const SMALLTALK = /^(how are you|what's up|what is up|who are you|what (can|do) you do|what is (this|mediassist)|help me|test|testing)[.!?]*$/i;
const SOCIAL = /^((i|we)\s+)?(miss|love)\s+you\b|^(miss you|love you|thinking of you|take care|good night|good luck|sweet dreams|see you soon)[.!?]*$/i;
const MEDICAL =
  /\b(pain|ache|aching|hurt|hurts|sore|fever|cough|cold|flu|vomit\w*|nause\w*|dizz\w*|rash|bleed\w*|breath\w*|chest|headache\w*|migraine|stomach|abdomen|throat|symptom\w*|illness|\bill\b|sick|infect\w*|swell\w*|diabet\w*|asthma|covid|pregnan\w*|period|urine|urinat\w*|\bpee\b|diarrhea|diarrhoea|constipat\w*|anxiety|depress\w*|insomni\w*|allerg\w*|wound|burns?|fracture|sprain|doctor|hospital|triage|diagnos\w*|medicine|medication|paracetamol|acetaminophen|ibuprofen|aspirin|nsaid|itchy|itching|fatigue|tired|lump|swelling|swollen|painful|knee|kneecap|ankle|calf|shin|thigh|runny nose|congestion|wheeze|cramp|bloating|heartburn|reflux|first aid|vaccin\w*|vitamin|nutrition|thyroid|cancer|cholesterol|smear|mammogram|screening|dementia|alzheimer|smok\w*|unwell|neck|droop|double vision|eyelid|something is wrong|feel unwell|blood pressure|treatment|prevent|mental health|injur\w*|bruise\w*|infection|diseases?|syndrome|disorder|\w+(itis|osis|emia|oma|pathy)|extra detail:|body map context)\b/i;
const EDUCATIONAL_MEDICAL =
  /\b(what causes|what is|what's|whats|explain|tell me about|describe|define|i want to (understand|know|learn)|help me understand|what \w[\w'-]*(?:\s+\w[\w'-]*){0,4}\s+is\b|symptoms of|how does .{0,40} feel|how is .{0,40} treated|treatments? (available|for)|rare disease|knowledge base|not in (my |the )?(notes|database|kb))\b/i;
const PERSONAL_SYMPTOM =
  /\b(i have|i've got|i have got|i am having|i'm having|i feel|my \w+ (hurts|ache|is sore)|it burns when|extra detail:|body map context)\b/i;
const NON_MEDICAL =
  /\b(travel from|travel to|distance (from|between|to)|how far (is|from)|book(ing)? (a )?flight|flight (to|from|number)|plane ticket|hotel|itinerary|weather|forecast|python|javascript|write (me )?(some )?code|programming|laptop|iphone|shopping|netflix|movie|stock price|bitcoin|should i (buy|get|choose|pick))\b|(?:what's|what\s+is|what\s+are|which(?:\s+one)?\s+(?:is|are))\s+(?:better|best|worse|faster|cheaper|easier|safer)\b|\bvs\.?\b|\bversus\b|\b(car|bike|bicycle|motorcycle|scooter|bus|train|plane|iphone|android|laptop|phone|tablet)\b.{0,50}\b(or|vs\.?|versus)\b|\b(or|vs\.?|versus)\b.{0,50}\b(car|bike|bicycle|motorcycle|scooter|bus|train|plane|iphone|android|laptop|phone|tablet)\b|print\s*\(|console\.log|def\s+\w+\s*\(|import\s+\w+/i;
const FOLLOWUP = /\b(also|as well|with that|tell me more|more about|second (one|condition|match)|first (one|condition|match)|what about|how about|worse|(getting|feeling|feels) better|it's better|it is better|is it better|still have|what could cause|what should i do|what can i do|warning signs|when should i seek|i meant|more simply|in simple(r)? (words|language|terms)|more detail|explain (that|this|it)|can it be treated)\b/i;
const FOLLOW_QUESTION =
  /\b(what could cause (this|it|that)|what (can|should) i do|what warning signs|when should i (seek|see|get) (help|care)|i meant|explain (that|this|it)|more simply|can (it|this) be treated)\b/i;

function plainQuery(text: string): string {
  return text
    .replace(/Body map context \(user-described discomfort, not a diagnosis\):[\s\S]*$/i, "")
    .replace(/\n\nExtra detail:[\s\S]*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function isEducationalMedicalQuery(text: string): boolean {
  return EDUCATIONAL_MEDICAL.test(text) && !PERSONAL_SYMPTOM.test(text);
}

export function isPersonalSymptomQuery(text: string): boolean {
  return PERSONAL_SYMPTOM.test(text) || /extra detail:|body map context/i.test(text);
}

export function looksMedical(text: string, history: ChatMessage[] = []): boolean {
  const raw = text.trim();
  if (!raw) return false;
  if (looksEmergency(raw)) return true;
  if (/body map context/i.test(raw) || /extra detail:/i.test(raw)) return true;
  const plain = plainQuery(raw);
  if (GREETING.test(plain) || WELLBEING.test(plain) || SMALLTALK.test(plain) || SOCIAL.test(plain)) return false;
  if (MEDICAL.test(plain)) return true;
  if (NON_MEDICAL.test(plain)) return false;
  const medicalThread = history.some(
    (item) => item.possible_conditions?.length || item.triage || MEDICAL.test(item.content || ""),
  );
  if (medicalThread && (FOLLOWUP.test(plain) || FOLLOW_QUESTION.test(plain))) return true;
  return false;
}

export function isOffTopicQuery(text: string): boolean {
  const plain = plainQuery(text);
  if (!plain) return false;
  if (GREETING.test(plain) || WELLBEING.test(plain) || SMALLTALK.test(plain) || SOCIAL.test(plain)) return true;
  if (MEDICAL.test(plain)) return false;
  return NON_MEDICAL.test(plain);
}

export function isConversationFollowUp(text: string): boolean {
  const plain = plainQuery(text);
  return FOLLOWUP.test(plain) || FOLLOW_QUESTION.test(plain);
}

export function needsSymptomIntake(text: string, messages: ChatMessage[]): boolean {
  if (looksEmergency(text)) return false;
  if (!looksMedical(text, messages)) return false;
  if (/extra detail:/i.test(text)) return false;
  if (isEducationalMedicalQuery(text)) return false;
  const medicalThread = messages.some(
    (item) => item.possible_conditions?.length || item.triage || looksMedical(item.content || "", []),
  );
  if (medicalThread) return false;
  return true;
}
