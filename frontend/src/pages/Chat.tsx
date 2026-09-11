import { useEffect, useRef } from "react";
import { Menu } from "lucide-react";
import { useParams } from "react-router-dom";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatInput } from "../components/chat/ChatInput";
import { MessageBubble } from "../components/chat/MessageBubble";
import { Spinner } from "../components/common/Spinner";
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
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

  function onScroll() {
    const node = scroller.current;
    if (!node) return;
    stickToBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-[linear-gradient(180deg,#f4f8f7_0%,#eaf3f1_100%)]">
      <ChatSidebar />
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-teal-100/80 bg-white/90 px-4 backdrop-blur">
          <div>
            <p className="text-sm font-extrabold text-slate-900">Symptom conversation</p>
            <p className="text-xs text-slate-500">Four possible matches, urgency, and sources — not a diagnosis.</p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-full border border-teal-100 px-3 py-1.5 text-sm font-bold text-teal-800 lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu size={16} /> Chats
          </button>
        </header>
        <div ref={scroller} onScroll={onScroll} className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-5">
            {messagesLoading ? <Spinner label="Loading conversation..." /> : null}
            {!messagesLoading && !messages.length ? (
              <div className="m-auto max-w-lg rounded-3xl border border-dashed border-teal-200 bg-white/80 px-6 py-10 text-center shadow-sm">
                <h2 className="text-xl font-extrabold text-slate-900">Describe your symptoms</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Each reply lists four possible matches with percentages, the urgency, and the citations used.
                </p>
              </div>
            ) : null}
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {streaming && status ? (
              <p className="pl-12 text-sm font-semibold text-teal-800">{status}</p>
            ) : null}
            {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800">{error}</p> : null}
          </div>
        </div>
        <ChatInput disabled={sending} streaming={streaming} onSend={(value) => void sendMessage(value)} onStop={stopGeneration} />
      </section>
    </div>
  );
}
