import { useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { useParams } from "react-router-dom";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatInput } from "../components/chat/ChatInput";
import { MessageBubble } from "../components/chat/MessageBubble";
import { FollowUpCard, formatFollowUpQuery, type FollowUpAnswers } from "../components/chat/FollowUpCard";
import { NearbyHospitals } from "../components/chat/NearbyHospitals";
import { EmergencyCallButton } from "../components/chat/EmergencyCallButton";
import { Spinner } from "../components/common/Spinner";
import { useChat } from "../context/ChatContext";
import { useApp } from "../context/AppContext";
import { looksEmergency } from "../utils/emergency";

export function Chat() {
  const { chatId } = useParams();
  const { loadChats, openChat, showBlankChat, messages, messagesLoading, sendMessage, stopGeneration, sending, streaming, status, error } = useChat();
  const { setSidebarOpen } = useApp();
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [pendingSymptoms, setPendingSymptoms] = useState<string | null>(null);

  useEffect(() => {
    void loadChats();
  }, [loadChats]);

  useEffect(() => {
    if (chatId) void openChat(chatId);
    else showBlankChat();
    setPendingSymptoms(null);
  }, [chatId, openChat, showBlankChat]);

  useEffect(() => {
    if (!stickToBottom.current) return;
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, status, pendingSymptoms]);

  function onScroll() {
    const node = scroller.current;
    if (!node) return;
    stickToBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
  }

  function handleSend(value: string) {
    if (looksEmergency(value)) {
      setPendingSymptoms(null);
      void sendMessage(value);
      return;
    }
    setPendingSymptoms(value);
  }

  function handleFollowUp(answers: FollowUpAnswers) {
    if (!pendingSymptoms) return;
    const query = formatFollowUpQuery(pendingSymptoms, answers);
    setPendingSymptoms(null);
    void sendMessage(query);
  }

  const latest = [...messages].reverse().find((item) => item.role === "assistant" && !item.streaming);
  const showHospitals = Boolean(latest && !latest.refused && (latest.possible_conditions.length || latest.triage || latest.citations.length));
  const urgent = latest?.triage?.level === "emergency";

  return (
    <div className="flex h-dvh overflow-hidden bg-[linear-gradient(180deg,#f4f8f7_0%,#eaf3f1_100%)]">
      <ChatSidebar />
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-teal-100/80 bg-white/90 px-4 backdrop-blur">
          <div>
            <p className="text-sm font-extrabold text-slate-900">Symptom conversation</p>
            <p className="text-xs text-slate-500">Four possible matches, urgency, sources, and nearby hospitals.</p>
          </div>
          <div className="flex items-center gap-2">
            <EmergencyCallButton urgent={urgent} />
            <button className="inline-flex items-center gap-2 rounded-full border border-teal-100 px-3 py-1.5 text-sm font-bold text-teal-800 lg:hidden" onClick={() => setSidebarOpen(true)}>
              <Menu size={16} /> Chats
            </button>
          </div>
        </header>
        <div ref={scroller} onScroll={onScroll} className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-5">
            {messagesLoading ? <Spinner label="Loading conversation..." /> : null}
            {!messagesLoading && !messages.length && !pendingSymptoms ? (
              <div className="m-auto max-w-lg rounded-3xl border border-dashed border-teal-200 bg-white/80 px-6 py-10 text-center shadow-sm">
                <h2 className="text-xl font-extrabold text-slate-900">Describe your symptoms</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  I will ask three short questions, then show matches, urgency, citations, and hospitals near you.
                </p>
              </div>
            ) : null}
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {pendingSymptoms ? (
              <FollowUpCard
                symptoms={pendingSymptoms}
                onContinue={handleFollowUp}
                onSkip={() => {
                  const text = pendingSymptoms;
                  setPendingSymptoms(null);
                  void sendMessage(text);
                }}
              />
            ) : null}
            {showHospitals && latest ? <NearbyHospitals key={latest.id} active /> : null}
            {streaming && status ? <p className="pl-12 text-sm font-semibold text-teal-800">{status}</p> : null}
            {error ? <p className="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800">{error}</p> : null}
          </div>
        </div>
        <ChatInput disabled={sending || Boolean(pendingSymptoms)} streaming={streaming} onSend={handleSend} onStop={stopGeneration} />
      </section>
    </div>
  );
}
