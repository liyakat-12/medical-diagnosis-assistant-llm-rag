import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import * as chatApi from "../services/chat";
import type { Chat, ChatMessage, StreamEvent } from "../types";
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
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
  renameChat: (chatId: string, title: string) => Promise<void>;
  removeChat: (chatId: string) => Promise<void>;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function assistantFromEvent(event: StreamEvent, fallback: ChatMessage): ChatMessage {
  const saved = event.message;
  if (saved) return { ...saved, streaming: false };
  const result = event.result || {};
  return {
    ...fallback,
    content: String(result.answer || fallback.content),
    citations: (result.citations as ChatMessage["citations"]) || fallback.citations,
    triage: (result.triage as ChatMessage["triage"]) || fallback.triage,
    possible_conditions: (result.possible_conditions as ChatMessage["possible_conditions"]) || fallback.possible_conditions,
    faithfulness: (result.faithfulness as ChatMessage["faithfulness"]) || fallback.faithfulness,
    recommendations: (result.recommendations as ChatMessage["recommendations"]) || fallback.recommendations,
    refused: Boolean(result.refused),
    disclaimer: (result.disclaimer as string) || fallback.disclaimer,
    streaming: false,
  };
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

  const loadChats = useCallback(async (query?: string) => {
    setChatsLoading(true);
    try {
      setChats(await chatApi.listChats(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load conversations.");
    } finally {
      setChatsLoading(false);
    }
  }, []);

  const openChat = useCallback(async (chatId: string) => {
    setActiveChatId(chatId);
    if (abortRef.current) return;
    setMessagesLoading(true);
    setError("");
    try {
      setMessages(await chatApi.listMessages(chatId));
    } catch (err) {
      setMessages([]);
      setError(err instanceof Error ? err.message : "Unable to load this conversation.");
    } finally {
      setMessagesLoading(false);
    }
  }, []);

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
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setSending(false);
    setStatus("");
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || sending) return;
      setError("");
      setSending(true);
      setStreaming(true);
      setStatus("Analyzing your symptoms...");

      let chatId = activeChatId;
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
        const assistantId = `temp-asst-${now}`;
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
        setMessages((current) => [...current, userMsg, assistantMsg]);

        const controller = new AbortController();
        abortRef.current = controller;
        await chatApi.streamMessage(
          chatId,
          text,
          (event) => {
            if (event.type === "status" && event.content) setStatus(event.content);
            if (event.type === "token" && event.content) {
              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantId ? { ...item, content: item.content + event.content } : item,
                ),
              );
            }
            if (event.type === "citation" && event.citations) {
              setMessages((current) =>
                current.map((item) => (item.id === assistantId ? { ...item, citations: event.citations || [] } : item)),
              );
            }
            if (event.type === "triage") {
              setMessages((current) =>
                current.map((item) =>
                  item.id === assistantId
                    ? {
                        ...item,
                        triage: {
                          level: event.level || "consult_doctor",
                          label: event.label || "Urgency",
                          guidance: event.guidance || "",
                        },
                      }
                    : item,
                ),
              );
            }
            if (event.type === "metadata") {
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
              setMessages((current) =>
                current.map((item) => (item.id === assistantId ? assistantFromEvent(event, item) : item)),
              );
            }
          },
          controller.signal,
        );
        await loadChats();
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          setStatus("");
          return;
        }
        setError(err instanceof Error ? err.message : "Unable to send your message. Please try again.");
      } finally {
        abortRef.current = null;
        setSending(false);
        setStreaming(false);
        setStatus("");
      }
    },
    [activeChatId, loadChats, navigate, sending],
  );

  const renameChat = useCallback(
    async (chatId: string, title: string) => {
      const updated = await chatApi.updateChat(chatId, { title });
      setChats((current) => current.map((item) => (item.id === chatId ? updated : item)));
      toast("Conversation renamed.");
    },
    [toast],
  );

  const removeChat = useCallback(
    async (chatId: string) => {
      await chatApi.deleteChat(chatId);
      setChats((current) => current.filter((item) => item.id !== chatId));
      if (activeChatId === chatId) {
        setActiveChatId(null);
        setMessages([]);
        navigate("/chat");
      }
      toast("Conversation deleted.");
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
