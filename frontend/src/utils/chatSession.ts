import type { ChatMessage, StreamEvent } from "../types";
import { PUBLIC_SEND_ERROR, publicError, publicStatus } from "./publicText";

export const INCOMPLETE_REPLY_NOTICE = "This reply was stopped before it finished.";

export interface ChatSessionState {
  activeChatId: string | null;
  messages: ChatMessage[];
  streaming: boolean;
  sending: boolean;
  status: string;
  error: string;
  failedContent: string | null;
  requestId: number;
  streamAssistantId: string | null;
  streamUserText: string | null;
  streamChatId: string | null;
}

export function emptySession(activeChatId: string | null = null): ChatSessionState {
  return {
    activeChatId,
    messages: [],
    streaming: false,
    sending: false,
    status: "",
    error: "",
    failedContent: null,
    requestId: 0,
    streamAssistantId: null,
    streamUserText: null,
    streamChatId: null,
  };
}

export function publicMessage(message: ChatMessage): ChatMessage {
  return { ...message, model: null };
}

export function isIncompleteMessage(message: ChatMessage): boolean {
  return Boolean(message.metadata?.incomplete) || (message.content || "").includes(INCOMPLETE_REPLY_NOTICE);
}

export function markAssistantIncomplete(message: ChatMessage, leftover = ""): ChatMessage {
  if (!message.streaming && isIncompleteMessage(message)) {
    return { ...message, streaming: false };
  }
  const partial = `${message.content || ""}${leftover}`.trim();
  const content = partial.includes(INCOMPLETE_REPLY_NOTICE)
    ? partial
    : partial
      ? `${partial}\n\n${INCOMPLETE_REPLY_NOTICE}`
      : INCOMPLETE_REPLY_NOTICE;
  return {
    ...message,
    content,
    streaming: false,
    possible_conditions: [],
    recommendations: [],
    triage: null,
    citations: [],
    metadata: { ...(message.metadata || {}), incomplete: true, evidence_origin: "none" },
  };
}

export function shouldAcceptStreamEvent(eventRequestId: number, activeRequestId: number): boolean {
  return eventRequestId === activeRequestId;
}

export function assistantFromEvent(event: StreamEvent, fallback: ChatMessage): ChatMessage {
  const saved = event.message;
  const result = event.result || {};
  const merged = saved ? { ...fallback, ...saved } : fallback;
  // Prefer the finalized API result so streamed title-dump tokens cannot override a corrected answer.
  const fromResult = typeof result.answer === "string" ? result.answer.trim() : "";
  const answer = String(fromResult || merged.content || fallback.content || "").trim();
  const triage = (() => {
    const value = (result.triage as ChatMessage["triage"]) || (merged.triage as ChatMessage["triage"]) || fallback.triage;
    if (!value || value.level === "none") return null;
    return value;
  })();
  const resultConditions = (result.possible_conditions as ChatMessage["possible_conditions"]) || [];
  const resultCitations = (result.citations as ChatMessage["citations"]) || [];
  return publicMessage({
    ...merged,
    content: answer || fallback.content,
    citations: resultCitations.length ? resultCitations : merged.citations?.length ? merged.citations : fallback.citations,
    triage,
    possible_conditions: resultConditions.length
      ? resultConditions
      : merged.possible_conditions?.length
        ? merged.possible_conditions
        : fallback.possible_conditions,
    faithfulness: (result.faithfulness as ChatMessage["faithfulness"]) ?? merged.faithfulness ?? fallback.faithfulness,
    recommendations: ((result.recommendations as string[]) || []).length
      ? (result.recommendations as string[])
      : merged.recommendations?.length
        ? merged.recommendations
        : fallback.recommendations,
    refused: Boolean(merged.refused ?? result.refused),
    disclaimer: merged.disclaimer || (result.disclaimer as string) || fallback.disclaimer,
    metadata: {
      ...(fallback.metadata || {}),
      ...(merged.metadata || {}),
      evidence_origin: result.evidence_origin || merged.metadata?.evidence_origin || fallback.metadata?.evidence_origin || "none",
      question_type: result.question_type || merged.metadata?.question_type || fallback.metadata?.question_type || "",
      personal_context: Boolean(result.personal_context ?? merged.metadata?.personal_context ?? fallback.metadata?.personal_context),
      incomplete: false,
    },
    streaming: false,
  });
}

function tempPair(chatId: string, text: string, now: string): { user: ChatMessage; assistant: ChatMessage } {
  return {
    user: {
      id: `temp-user-${now}`,
      chat_id: chatId,
      user_id: "",
      role: "user",
      content: text,
      created_at: now,
      citations: [],
      possible_conditions: [],
      recommendations: [],
      refused: false,
    },
    assistant: {
      id: `temp-asst-${now}`,
      chat_id: chatId,
      user_id: "",
      role: "assistant",
      content: "",
      created_at: now,
      citations: [],
      possible_conditions: [],
      recommendations: [],
      refused: false,
      streaming: true,
    },
  };
}

export function beginSend(state: ChatSessionState, chatId: string, text: string, reuseFailed = false, now = new Date().toISOString()): ChatSessionState {
  const requestId = state.requestId + 1;
  const { user, assistant } = tempPair(chatId, text, now);
  let messages = [...state.messages];
  if (reuseFailed) {
    if (messages.at(-1)?.role === "assistant") messages.pop();
    if (!(messages.at(-1)?.role === "user" && messages.at(-1)?.content === text)) {
      messages = [...messages, user];
    }
    messages = [...messages, assistant];
  } else {
    messages = [...messages, user, assistant];
  }
  return {
    ...state,
    activeChatId: chatId,
    messages,
    sending: true,
    streaming: true,
    status: "Understanding your message...",
    error: "",
    failedContent: null,
    requestId,
    streamAssistantId: assistant.id,
    streamUserText: text,
    streamChatId: chatId,
  };
}

export function applyStreamEvent(state: ChatSessionState, event: StreamEvent, eventRequestId: number): ChatSessionState {
  if (!shouldAcceptStreamEvent(eventRequestId, state.requestId) || !state.streamAssistantId) return state;
  if (state.streamChatId && state.activeChatId && state.streamChatId !== state.activeChatId) return state;
  const assistantId = state.streamAssistantId;
  const mapAssistant = (update: (item: ChatMessage) => ChatMessage): ChatMessage[] =>
    state.messages.map((item) => (item.id === assistantId ? update(item) : item));

  if (event.type === "status" && event.content) {
    return { ...state, status: publicStatus(event.content) };
  }
  if (event.type === "token" && event.content) {
    return {
      ...state,
      messages: mapAssistant((item) => ({ ...item, content: item.content + event.content })),
    };
  }
  if (event.type === "citation") {
    return {
      ...state,
      messages: mapAssistant((item) => ({
        ...item,
        citations: event.citations || item.citations,
        possible_conditions: event.possible_conditions || item.possible_conditions,
      })),
    };
  }
  if (event.type === "triage" && event.level && event.level !== "none") {
    const level = event.level;
    return {
      ...state,
      messages: mapAssistant((item) => ({
        ...item,
        triage: {
          level,
          label: event.label || "Urgency",
          guidance: event.guidance || "",
          reason: event.reason,
        },
      })),
    };
  }
  if (event.type === "done") {
    return {
      ...state,
      messages: mapAssistant((item) => assistantFromEvent(event, item)),
      streaming: false,
      sending: false,
      status: "",
      streamAssistantId: null,
      streamUserText: null,
      streamChatId: null,
    };
  }
  return state;
}

export function abortStream(state: ChatSessionState, leftover = ""): ChatSessionState {
  if (!state.streamAssistantId && !state.streaming) return state;
  const assistantId = state.streamAssistantId;
  return {
    ...state,
    messages: assistantId
      ? state.messages.map((item) => (item.id === assistantId && item.streaming ? markAssistantIncomplete(item, leftover) : item))
      : state.messages,
    streaming: false,
    sending: false,
    status: "",
    error: "",
    failedContent: state.streamUserText || state.failedContent,
    requestId: state.requestId + 1,
    streamAssistantId: null,
    streamUserText: state.streamUserText,
    streamChatId: null,
  };
}

export function failSend(state: ChatSessionState, message?: string): ChatSessionState {
  const assistantId = state.streamAssistantId;
  return {
    ...state,
    messages: assistantId
      ? state.messages.map((item) => (item.id === assistantId && item.streaming ? markAssistantIncomplete(item) : item))
      : state.messages,
    streaming: false,
    sending: false,
    status: "",
    error: publicError(message, PUBLIC_SEND_ERROR),
    failedContent: state.streamUserText || state.failedContent,
    requestId: state.requestId + 1,
    streamAssistantId: null,
    streamChatId: null,
  };
}

export function reloadMessages(state: ChatSessionState, chatId: string, serverMessages: ChatMessage[]): ChatSessionState {
  return {
    ...emptySession(chatId),
    messages: serverMessages.map(publicMessage),
    requestId: state.requestId + 1,
  };
}

export function switchChat(state: ChatSessionState, chatId: string, serverMessages: ChatMessage[]): ChatSessionState {
  const aborted = state.streaming && state.activeChatId && state.activeChatId !== chatId ? abortStream(state) : state;
  return reloadMessages(aborted, chatId, serverMessages);
}

export function canRetry(state: ChatSessionState): boolean {
  if (state.sending || state.streaming) return false;
  return Boolean(state.failedContent) || Boolean(state.messages.at(-1) && isIncompleteMessage(state.messages.at(-1)!));
}
