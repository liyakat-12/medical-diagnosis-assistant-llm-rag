import { useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatInput } from "../components/chat/ChatInput";
import { MessageBubble } from "../components/chat/MessageBubble";
import { EmptyState, Spinner } from "../components/common/Spinner";
import { useChat } from "../context/ChatContext";
import { useApp } from "../context/AppContext";

export function Chat() {
  const { chatId } = useParams();
  const { loadChats, openChat, showBlankChat, messages, messagesLoading, sendMessage, stopGeneration, sending, streaming, status, error } = useChat();
  const { setSidebarOpen } = useApp();
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  useEffect(() => {
    void loadChats();
  }, [loadChats]);

  useEffect(() => {
    if (chatId) void openChat(chatId);
    else showBlankChat();
  }, [chatId, openChat, showBlankChat]);

  useEffect(() => {
    if (!stickToBottom.current) return;
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages, status]);

  function onScroll() {
    const node = scroller.current;
    if (!node) return;
    stickToBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-[#f4f8f7]">
      <ChatSidebar />
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-teal-100 bg-white px-4">
          <div>
            <p className="text-sm font-extrabold text-slate-900">Symptom conversation</p>
            <p className="text-xs text-slate-500">General information and triage — not a diagnosis.</p>
          </div>
          <button className="text-sm font-bold text-teal-800 lg:hidden" onClick={() => setSidebarOpen(true)}>
            Chats
          </button>
        </header>
        <div ref={scroller} onScroll={onScroll} className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
          {messagesLoading ? <Spinner label="Loading conversation..." /> : null}
          {!messagesLoading && !messages.length ? (
            <EmptyState title="Tell me what symptoms you're experiencing." body="Describe onset, location, and anything that makes it better or worse. Emergency signs are highlighted immediately." />
          ) : null}
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {streaming && status ? <p className="text-sm font-semibold text-teal-800">{status}</p> : null}
          {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800">{error}</p> : null}
        </div>
        <ChatInput disabled={sending} streaming={streaming} onSend={(value) => void sendMessage(value)} onStop={stopGeneration} />
      </section>
    </div>
  );
}
