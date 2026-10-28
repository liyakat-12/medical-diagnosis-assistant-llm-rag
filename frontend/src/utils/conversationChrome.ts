import type { ChatMessage } from "../types";
import { looksEmergency } from "./emergency";
import {
  isConversationFollowUp,
  isEducationalMedicalQuery,
  isOffTopicQuery,
  isPersonalSymptomQuery,
  looksMedical,
} from "./intent";
import { isSymptomCardMessage } from "./report";

export interface ConversationChrome {
  title: string;
  subtitle: string;
  emphasizeEmergency: boolean;
}

const EMERGENCY: ConversationChrome = {
  title: "Emergency help",
  subtitle: "If this is an emergency, call 112. Not a diagnosis.",
  emphasizeEmergency: true,
};

const SYMPTOM: ConversationChrome = {
  title: "Symptom conversation",
  subtitle: "Matches, urgency, sources, and nearby hospitals. Not a diagnosis.",
  emphasizeEmergency: false,
};

const HEALTH: ConversationChrome = {
  title: "Health information",
  subtitle: "General medical information. Not a diagnosis.",
  emphasizeEmergency: false,
};

const DEFAULT: ConversationChrome = {
  title: "MediAssist",
  subtitle: "Ask a health question or tap where it hurts. Not a diagnosis.",
  emphasizeEmergency: false,
};

function lastUserIndex(messages: ChatMessage[]): number {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "user") return index;
  }
  return -1;
}

function turnIsEmergency(user: ChatMessage, assistant: ChatMessage | undefined, prior: ChatMessage[]): boolean {
  if (looksEmergency(user.content || "", prior)) return true;
  return assistant?.triage?.level === "emergency";
}

function latestAssistant(messages: ChatMessage[], userIndex: number): ChatMessage | undefined {
  return messages.slice(userIndex + 1).find((item) => item.role === "assistant");
}

function inheritedEmergency(messages: ChatMessage[], userIndex: number): boolean {
  const latest = messages[userIndex];
  if (!latest || !isConversationFollowUp(latest.content || "")) return false;
  if (isOffTopicQuery(latest.content || "")) return false;
  for (let index = userIndex - 1; index >= 0; index -= 1) {
    const item = messages[index];
    if (item.role !== "user") {
      if (item.triage?.level === "emergency") return true;
      continue;
    }
    if (isOffTopicQuery(item.content || "") || isConversationFollowUp(item.content || "")) continue;
    return turnIsEmergency(item, latestAssistant(messages, index), messages.slice(0, index));
  }
  return false;
}

export function conversationChrome(messages: ChatMessage[]): ConversationChrome {
  const userIndex = lastUserIndex(messages);
  const latestUser = userIndex >= 0 ? messages[userIndex] : null;
  const assistant = userIndex >= 0 ? latestAssistant(messages, userIndex) : undefined;

  if (latestUser && isOffTopicQuery(latestUser.content || "")) {
    return DEFAULT;
  }

  if (latestUser && (turnIsEmergency(latestUser, assistant, messages.slice(0, userIndex)) || inheritedEmergency(messages, userIndex))) {
    return EMERGENCY;
  }

  const latestType = String(assistant?.metadata?.question_type || "");
  const latestPersonal = assistant?.metadata?.personal_context === true;
  const referenceType = ["MEDICAL_EDUCATION", "TREATMENT_INFORMATION", "MEDICATION_SAFETY"].includes(latestType)
    || (!latestPersonal && ["SYMPTOM_INFORMATION", "POSSIBLE_CAUSES", "FOLLOW_UP"].includes(latestType));
  if (latestUser && isEducationalMedicalQuery(latestUser.content || "") && !isPersonalSymptomQuery(latestUser.content || "")) {
    return HEALTH;
  }
  if (referenceType && assistant?.triage?.level !== "emergency") {
    return HEALTH;
  }

  const hasSymptomAssessment = messages.some(
    (item) =>
      isSymptomCardMessage(item) ||
      (item.role === "user" && isPersonalSymptomQuery(item.content || "") && !isEducationalMedicalQuery(item.content || "")),
  );
  if (hasSymptomAssessment) return SYMPTOM;

  const hasMedicalInfo = messages.some((item) => item.role === "user" && looksMedical(item.content || "", messages));
  if (hasMedicalInfo) return HEALTH;

  return DEFAULT;
}
