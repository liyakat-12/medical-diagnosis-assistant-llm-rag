import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import type { ChatMessage } from "../src/types/index.ts";
import {
  INCOMPLETE_REPLY_NOTICE,
  abortStream,
  applyStreamEvent,
  beginSend,
  canRetry,
  emptySession,
  failSend,
  isIncompleteMessage,
  reloadMessages,
  switchChat,
} from "../src/utils/chatSession.ts";
import { conversationChrome } from "../src/utils/conversationChrome.ts";
import { looksEmergency } from "../src/utils/emergency.ts";
import { isConversationFollowUp, isOffTopicQuery, looksMedical } from "../src/utils/intent.ts";
import { publicError } from "../src/utils/publicText.ts";
import { formatAssistantCopy } from "../src/utils/report.ts";

const chatContextSource = readFileSync(new URL("../src/context/ChatContext.tsx", import.meta.url), "utf8");
const chatPageSource = readFileSync(new URL("../src/pages/Chat.tsx", import.meta.url), "utf8");
const bubbleSource = readFileSync(new URL("../src/components/chat/MessageBubble.tsx", import.meta.url), "utf8");
const inputSource = readFileSync(new URL("../src/components/chat/ChatInput.tsx", import.meta.url), "utf8");

function message(partial: Partial<ChatMessage>): ChatMessage {
  return {
    id: "1",
    chat_id: "c",
    user_id: "u",
    role: "user",
    content: "",
    citations: [],
    possible_conditions: [],
    recommendations: [],
    refused: false,
    ...partial,
  };
}

describe("ui01 abort during streaming", () => {
  it("clears streaming and marks the assistant row incomplete without deleting the user message", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a dry cough at night", false, "2026-01-01T00:00:00.000Z");
    state = applyStreamEvent(state, { type: "token", content: "A leftover" }, state.requestId);
    const requestId = state.requestId;
    state = abortStream(state, " cough.");
    assert.equal(state.streaming, false);
    assert.equal(state.sending, false);
    assert.equal(state.messages.length, 2);
    assert.equal(state.messages[0].role, "user");
    assert.equal(state.messages[0].content, "I have a dry cough at night");
    assert.equal(state.messages[1].streaming, false);
    assert.equal(isIncompleteMessage(state.messages[1]), true);
    assert.match(state.messages[1].content, new RegExp(INCOMPLETE_REPLY_NOTICE));
    assert.equal(state.messages[1].possible_conditions.length, 0);
    assert.equal(state.failedContent, "I have a dry cough at night");
    assert.equal(canRetry(state), true);
    const late = applyStreamEvent(
      state,
      {
        type: "done",
        result: {
          answer: "Possible leftover viral cough.",
          possible_conditions: [{ condition: "Dry Cough", match_percent: 100 }],
        },
      },
      requestId,
    );
    assert.equal(late.messages[1].possible_conditions.length, 0);
    assert.equal(isIncompleteMessage(late.messages[1]), true);
  });

  it("wires abort into ChatContext", () => {
    assert.match(chatContextSource, /markAssistantIncomplete/);
    assert.match(chatContextSource, /shouldAcceptStreamEvent/);
    assert.match(chatContextSource, /failedContentRef\.current = meta\.userText/);
  });
});

describe("ui02 retry after a failed send", () => {
  it("resends the same user text without adding a second user bubble", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a dry cough at night", false, "t1");
    state = failSend(state, "Unable to send your message. Please try again.");
    assert.equal(state.error.includes("try again"), true);
    assert.equal(state.failedContent, "I have a dry cough at night");
    const before = state.messages.filter((item) => item.role === "user").length;
    state = beginSend(state, "chat-a", state.failedContent || "", true, "t2");
    assert.equal(state.messages.filter((item) => item.role === "user").length, before);
    assert.equal(state.messages.at(-1)?.streaming, true);
    assert.equal(isIncompleteMessage(state.messages.at(-1)!), false);
  });
});

describe("ui03 refresh / reopen a chat", () => {
  it("replaces temp streaming ids with the server list", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a cough", false, "temp");
    const server = [
      message({ id: "u1", chat_id: "chat-a", content: "I have a cough" }),
      message({
        id: "a1",
        chat_id: "chat-a",
        role: "assistant",
        content: "A leftover viral cough may linger.",
        possible_conditions: [{ condition: "Dry Cough", match_percent: 100 }],
      }),
    ];
    state = reloadMessages(state, "chat-a", server);
    assert.equal(state.messages.some((item) => item.id.startsWith("temp-")), false);
    assert.equal(state.messages.length, 2);
    assert.equal(state.streaming, false);
    assert.equal(state.messages[1].content.includes(INCOMPLETE_REPLY_NOTICE), false);
  });
});

describe("ui04 switch chats during or after a stream", () => {
  it("does not append chat A tokens onto chat B", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a cough", false, "a");
    const aRequest = state.requestId;
    const bMessages = [message({ id: "b-user", chat_id: "chat-b", content: "hello" })];
    state = switchChat(state, "chat-b", bMessages);
    assert.equal(state.activeChatId, "chat-b");
    assert.equal(state.messages.every((item) => item.chat_id === "chat-b"), true);
    const after = applyStreamEvent(state, { type: "token", content: "cough leftover" }, aRequest);
    assert.equal(after.messages.some((item) => item.content.includes("cough leftover")), false);
    assert.equal(after.messages[0].content, "hello");
  });

  it("does not accept chat A tokens into a new send in chat B", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a cough", false, "a");
    const aRequest = state.requestId;
    state = switchChat(state, "chat-b", []);
    state = beginSend(state, "chat-b", "hello", false, "b");
    assert.notEqual(state.requestId, aRequest);
    const after = applyStreamEvent(state, { type: "token", content: "cough leftover" }, aRequest);
    assert.equal(after.messages.some((item) => item.content.includes("cough leftover")), false);
  });
});

describe("ui05 emergency header state", () => {
  it("does not keep Emergency help after an unrelated later turn", () => {
    const chrome = conversationChrome([
      message({ content: "I have severe crushing chest pain spreading to my jaw" }),
      message({
        id: "2",
        role: "assistant",
        content: "Call 112.",
        triage: { level: "emergency", label: "Seek emergency care", guidance: "Call 112 now." },
      }),
      message({ id: "3", content: "Write a Python function for Fibonacci numbers" }),
      message({ id: "4", role: "assistant", content: "Here is an example." }),
    ]);
    assert.equal(chrome.title, "MediAssist");
    assert.equal(chrome.emphasizeEmergency, false);
  });

  it("keeps emergency chrome for a follow-up on the same complaint", () => {
    const chrome = conversationChrome([
      message({ content: "I have severe crushing chest pain spreading to my jaw" }),
      message({
        id: "2",
        role: "assistant",
        content: "Call 112.",
        triage: { level: "emergency", label: "Seek emergency care", guidance: "Call 112 now." },
      }),
      message({ id: "3", content: "What should I do?" }),
    ]);
    assert.equal(chrome.title, "Emergency help");
    assert.equal(chrome.emphasizeEmergency, true);
  });

  it("does not carry emergency chrome into another chat's messages", () => {
    const chatB = conversationChrome([message({ id: "b1", chat_id: "b", content: "hello" })]);
    assert.equal(chatB.emphasizeEmergency, false);
    assert.equal(chatB.title, "MediAssist");
  });
});

describe("ui06 copy includes answer and citations", () => {
  it("copies answer, sources, and evidence status without provider names", () => {
    const copy = formatAssistantCopy(
      message({
        role: "assistant",
        content: "A leftover viral cough may linger.",
        possible_conditions: [{ condition: "Dry Cough", match_percent: 100 }],
        triage: { level: "self_care", label: "Self care", guidance: "Rest." },
        citations: [
          { title: "Dry Cough at Night", source: "Sample KB" },
          { title: "General medical knowledge was used and was not verified against the knowledge base" },
        ],
      }),
    );
    assert.match(copy, /leftover viral cough/);
    assert.match(copy, /Dry Cough at Night/);
    assert.match(copy, /Evidence status/);
    assert.equal(/\b(groq|openai|ollama|chatgpt)\b/i.test(copy), false);
    assert.match(bubbleSource, /formatAssistantCopy/);
    assert.match(bubbleSource, /Copy/);
  });
});

describe("ui07 composer after error", () => {
  it("keeps a public error and restores the draft in ChatInput", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a cough", false, "t1");
    state = failSend(state, "Groq 429 rate limit");
    assert.equal(state.error, "Unable to send your message. Please try again.");
    assert.equal(publicError("Groq API key missing"), "Unable to send your message. Please try again.");
    assert.match(inputSource, /if \(!error\) return/);
    assert.match(inputSource, /draftRef\.current/);
    assert.match(inputSource, /setValue\(draftRef\.current\.value\)/);
    assert.match(chatPageSource, /error=\{error\}/);
    assert.equal(state.sending, false);
  });
});

describe("ui08 incomplete stream rendering", () => {
  it("does not keep finished match cards on an aborted assistant row", () => {
    let state = emptySession("chat-a");
    state = beginSend(state, "chat-a", "I have a cough", false, "t1");
    state = applyStreamEvent(
      state,
      { type: "citation", possible_conditions: [{ condition: "Dry Cough", match_percent: 80 }] },
      state.requestId,
    );
    state = abortStream(state);
    assert.equal(state.messages[1].possible_conditions.length, 0);
    assert.equal(state.messages[1].streaming, false);
    assert.match(state.messages[1].content, /stopped before it finished/i);
    assert.match(bubbleSource, /isIncompleteMessage/);
    assert.match(chatPageSource, /This reply was stopped before it finished/);
  });
});

describe("follow-up and calf intent helpers used by chrome", () => {
  it("treats everyday advice questions as follow-ups once a medical thread exists", () => {
    const history = [message({ content: "I have a cough", possible_conditions: [{ condition: "Cold" }] })];
    assert.equal(looksMedical("What should I do?", history), true);
    assert.equal(isConversationFollowUp("What could cause this?"), true);
    assert.equal(isOffTopicQuery("Write a Python function for Fibonacci numbers"), true);
    assert.equal(looksMedical("I have a swollen painful calf after a long flight"), true);
  });

  it("escalates breathless after a calf-and-flight history only", () => {
    const history = [message({ content: "I have a swollen painful calf after a long flight" })];
    assert.equal(looksEmergency("Now I feel breathless", history), true);
    assert.equal(looksEmergency("Now I feel breathless"), false);
    assert.equal(looksEmergency("I feel breathless after a flight of stairs"), false);
  });
});
