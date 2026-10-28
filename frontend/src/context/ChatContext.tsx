import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import * as chatApi from "../services/chat";
import type { Chat, ChatMessage } from "../types";
import { assistantFromEvent, markAssistantIncomplete, publicMessage, shouldAcceptStreamEvent } from "../utils/chatSession";
import { PUBLIC_SEND_ERROR, publicError, publicStatus } from "../utils/publicText";
import { useApp } from "./AppContext";

interface ChatContextValue {
  chats: Chat[];
  chatsLoading: boolean;
  messages: ChatMessage[];
  messagesLoading: boolean;
  activeChatId: string | null;
  sending: boolean;
  streaming: boolean;
  status: string;
  error: string;
  loadChats: (query?: string) => Promise<void>;
  openChat: (chatId: string) => Promise<void>;
  showBlankChat: () => void;
  startNewChat: () => Promise<Chat>;
  sendMessage: (content: string, options?: { reuseFailed?: boolean }) => Promise<void>;
  stopGeneration: () => void;
  retryLast: () => Promise<void>;
  renameChat: (chatId: string, title: string) => Promise<void>;
  removeChat: (chatId: string) => Promise<void>;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function localChatTitle(text: string): string {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) return "New chat";
  return cleaned.length > 52 ? `${cleaned.slice(0, 52).replace(/\s+\S*$/, "")}…` : cleaned;
}


export function ChatProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { toast, setSidebarOpen } = useApp();
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatsLoading, setChatsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const failedContentRef = useRef<string | null>(null);
  const sendingRef = useRef(false);
  const tokenBufferRef = useRef("");
  const tokenFlushRef = useRef<number | null>(null);
  const requestIdRef = useRef(0);
  const streamMetaRef = useRef<{ requestId: number; assistantId: string; userText: string; chatId: string } | null>(null);

  const stopActiveStream = (markIncomplete = true) => {
    const meta = streamMetaRef.current;
    const leftover = tokenBufferRef.current;
    if (tokenFlushRef.current != null) {
      window.cancelAnimationFrame(tokenFlushRef.current);
      tokenFlushRef.current = null;
    }
    tokenBufferRef.current = "";
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    sendingRef.current = false;
    setStreaming(false);
    setSending(false);
    setStatus("");
    if (markIncomplete && meta) {
      requestIdRef.current += 1;
      failedContentRef.current = meta.userText;
      setMessages((current) =>
        current.map((item) => (item.id === meta.assistantId && item.streaming ? markAssistantIncomplete(item, leftover) : item)),
      );
    }
    streamMetaRef.current = null;
  };

  const loadChats = useCallback(async (query?: string) => {
    setChatsLoading(true);
    try {
      setChats(await chatApi.listChats(query));
    } catch (err) {
      setError(publicError(err instanceof Error ? err.message : "Unable to load conversations."));
    } finally {
      setChatsLoading(false);
    }
  }, []);

  const openChat = useCallback(async (chatId: string) => {
    if (abortRef.current) {
      if (activeChatId && activeChatId !== chatId) stopActiveStream();
      else return;
    }
    setActiveChatId(chatId);
    setMessagesLoading(true);
    setError("");
    try {
      setMessages((await chatApi.listMessages(chatId)).map(publicMessage));
    } catch (err) {
      setMessages([]);
      setError(publicError(err instanceof Error ? err.message : "Unable to load this conversation."));
    } finally {
      setMessagesLoading(false);
    }
  }, [activeChatId]);

  const showBlankChat = useCallback(() => {
    if (abortRef.current) return;
    setActiveChatId(null);
    setMessages([]);
    setError("");
  }, []);

  const startNewChat = useCallback(async () => {
    const created = await chatApi.createChat();
    setChats((current) => [created, ...current.filter((item) => item.id !== created.id)]);
    setActiveChatId(created.id);
    setMessages([]);
    setSidebarOpen(false);
    navigate(`/chat/${created.id}`);
    return created;
  }, [navigate, setSidebarOpen]);

  const stopGeneration = useCallback(() => {
    stopActiveStream();
  }, []);

  const sendMessage = useCallback(
    async (content: string, options?: { reuseFailed?: boolean }) => {
      const text = content.trim();
      if (!text || sendingRef.current) return;
      setError("");
      failedContentRef.current = null;
      sendingRef.current = true;
      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      setSending(true);
      setStreaming(true);
      setStatus("Understanding your message...");

      let chatId = activeChatId;
      let assistantId = "";
      try {
        if (!chatId) {
          const created = await chatApi.createChat();
          chatId = created.id;
          setChats((current) => [created, ...current]);
          setActiveChatId(created.id);
          navigate(`/chat/${created.id}`, { replace: true });
        }

        const now = new Date().toISOString();
        const userMsg: ChatMessage = {
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
        };
        assistantId = `temp-asst-${now}`;
        const assistantMsg: ChatMessage = {
          id: assistantId,
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
        };
        setMessages((current) => {
          if (!options?.reuseFailed) return [...current, userMsg, assistantMsg];
          const next = [...current];
          if (next.at(-1)?.role === "assistant") next.pop();
          if (next.at(-1)?.role === "user" && next.at(-1)?.content === text) return [...next, assistantMsg];
          return [...next, userMsg, assistantMsg];
        });

        const controller = new AbortController();
        abortRef.current = controller;
        streamMetaRef.current = { requestId, assistantId, userText: text, chatId };
        const flushTokens = () => {
          if (tokenFlushRef.current != null) {
            window.cancelAnimationFrame(tokenFlushRef.current);
            tokenFlushRef.current = null;
          }
          const extra = tokenBufferRef.current;
          tokenBufferRef.current = "";
          if (!extra) return;
          setMessages((current) =>
            current.map((item) => (item.id === assistantId ? { ...item, content: item.content + extra } : item)),
          );
        };
        await chatApi.streamMessage(
          chatId,
          text,
          (event) => {
            if (!shouldAcceptStreamEvent(requestId, requestIdRef.current)) return;
            if (event.type === "status" && event.content) setStatus(publicStatus(event.content));
            if (event.type === "token" && event.content) {
              tokenBufferRef.current += event.content;
              if (tokenFlushRef.current == null) {
                tokenFlushRef.current = window.requestAnimationFrame(() => {
                  tokenFlushRef.current = null;
                  if (!shouldAcceptStreamEvent(requestId, requestIdRef.current)) return;
                  flushTokens();
                });
              }
            }
            if (event.type === "citation") {
              flushTokens();
              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantId
                    ? {
                        ...item,
                        citations: event.citations || item.citations,
                        possible_conditions: event.possible_conditions || item.possible_conditions,
                        metadata: {
                          ...(item.metadata || {}),
                          evidence_origin: (event.citations || []).some((row) =>
                            /not verified|General AI medical knowledge|not in local notes/i.test(
                              `${row.source || ""} ${row.title || ""}`,
                            ),
                          )
                            ? "llm"
                            : item.metadata?.evidence_origin,
                        },
                      }
                    : item,
                ),
              );
            }
            if (event.type === "triage" && event.level && event.level !== "none") {
              flushTokens();
              const level = event.level;
              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantId
                    ? {
                        ...item,
                        triage: {
                          level,
                          label: event.label || "Urgency",
                          guidance: event.guidance || "",
                          reason: event.reason,
                        },
                      }
                    : item,
                ),
              );
            }
            if (event.type === "metadata") {
              flushTokens();
              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantId
                    ? {
                        ...item,
                        recommendations: event.recommendations || item.recommendations,
                        faithfulness: event.faithfulness ?? item.faithfulness,
                      }
                    : item,
                ),
              );
            }
            if (event.type === "done") {
              if (!shouldAcceptStreamEvent(requestId, requestIdRef.current)) return;
              flushTokens();
              setMessages((current) =>
                current.map((item) => (item.id === assistantId && item.streaming ? assistantFromEvent(event, item) : item)),
              );
            }
          },
          controller.signal,
        );
        setChats((current) => {
          const updated = current.map((item) =>
            item.id === chatId
              ? {
                  ...item,
                  title: item.title === "New chat" ? localChatTitle(text) : item.title,
                  updated_at: now,
                  last_message_at: now,
                  message_count: Math.max(item.message_count || 0, 0) + (options?.reuseFailed ? 1 : 2),
                }
              : item,
          );
          const active = updated.find((item) => item.id === chatId);
          return active ? [active, ...updated.filter((item) => item.id !== chatId)] : updated;
        });
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setStatus("");
          return;
        }
        failedContentRef.current = text;
        setError(publicError(err instanceof Error ? err.message : PUBLIC_SEND_ERROR, PUBLIC_SEND_ERROR));
        if (assistantId) {
          setMessages((current) =>
            current.map((item) => (item.id === assistantId && item.streaming ? markAssistantIncomplete(item) : item)),
          );
        }
      } finally {
        abortRef.current = null;
        if (tokenFlushRef.current != null) {
          window.cancelAnimationFrame(tokenFlushRef.current);
          tokenFlushRef.current = null;
        }
        const leftover = tokenBufferRef.current;
        tokenBufferRef.current = "";
        if (leftover) {
          setMessages((current) =>
            current.map((item) =>
              item.streaming && item.role === "assistant" && !item.content.includes(leftover)
                ? { ...item, content: item.content + leftover }
                : item,
            ),
          );
        }
        sendingRef.current = false;
        setSending(false);
        setStreaming(false);
        setStatus("");
        if (streamMetaRef.current?.requestId === requestId) streamMetaRef.current = null;
      }
    },
    [activeChatId, navigate],
  );

  const retryLast = useCallback(async () => {
    const text = failedContentRef.current;
    if (!text || sending) return;
    await sendMessage(text, { reuseFailed: true });
  }, [sendMessage, sending]);

  const renameChat = useCallback(
    async (chatId: string, title: string) => {
      try {
        const updated = await chatApi.updateChat(chatId, { title });
        setChats((current) => current.map((item) => (item.id === chatId ? updated : item)));
        toast("Conversation renamed.");
      } catch (err) {
        setError(publicError(err instanceof Error ? err.message : "Unable to rename this conversation."));
      }
    },
    [toast],
  );

  const removeChat = useCallback(
    async (chatId: string) => {
      try {
        await chatApi.deleteChat(chatId);
        setChats((current) => current.filter((item) => item.id !== chatId));
        if (activeChatId === chatId) {
          setActiveChatId(null);
          setMessages([]);
          navigate("/chat");
        }
        toast("Conversation deleted.");
      } catch (err) {
        setError(publicError(err instanceof Error ? err.message : "Unable to delete this conversation."));
      }
    },
    [activeChatId, navigate, toast],
  );

  const value = useMemo(
    () => ({
      chats,
      chatsLoading,
      messages,
      messagesLoading,
      activeChatId,
      sending,
      streaming,
      status,
      error,
      loadChats,
      openChat,
      showBlankChat,
      startNewChat,
      sendMessage,
      stopGeneration,
      retryLast,
      renameChat,
      removeChat,
      clearError: () => setError(""),
    }),
    [
      chats,
      chatsLoading,
      messages,
      messagesLoading,
      activeChatId,
      sending,
      streaming,
      status,
      error,
      loadChats,
      openChat,
      showBlankChat,
      startNewChat,
      sendMessage,
      stopGeneration,
      retryLast,
      renameChat,
      removeChat,
    ],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
