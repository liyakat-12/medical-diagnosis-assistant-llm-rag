import { useEffect, useRef, useState } from "react";
import { ArrowDown, Menu, PanelLeft } from "lucide-react";
import { useParams } from "react-router-dom";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatInput, type ChatInputHandle } from "../components/chat/ChatInput";
import { BodyFigure } from "../components/chat/BodyMap";
import { REGION_LABELS, REGION_ORDER, type BodyRegion } from "../utils/bodyMap";
import { MessageBubble } from "../components/chat/MessageBubble";
import { FollowUpCard, formatFollowUpQuery, type FollowUpAnswers } from "../components/chat/FollowUpCard";
import { NearbyHospitals } from "../components/chat/NearbyHospitals";
import { EmergencyCallButton } from "../components/chat/EmergencyCallButton";
import { Spinner } from "../components/common/Spinner";
import { Button } from "../components/common/Button";
import { useChat } from "../context/ChatContext";
import { useApp } from "../context/AppContext";
import { looksEmergency } from "../utils/emergency";

export function Chat() {
  const { chatId } = useParams();
  const { loadChats, openChat, showBlankChat, activeChatId, messages, messagesLoading, sendMessage, stopGeneration, sending, streaming, status, error, clearError } = useChat();
  const { setSidebarOpen, sidebarCollapsed, setSidebarCollapsed } = useApp();
  const composerRef = useRef<ChatInputHandle>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [pendingSymptoms, setPendingSymptoms] = useState<string | null>(null);
  const [showJump, setShowJump] = useState(false);

  useEffect(() => {
    void loadChats();
  }, [loadChats]);

  useEffect(() => {
    if (chatId) {
      if (chatId === activeChatId && (sending || streaming)) return;
      void openChat(chatId);
    } else {
      showBlankChat();
    }
    setPendingSymptoms(null);
  }, [chatId, activeChatId, sending, streaming, openChat, showBlankChat]);

  useEffect(() => {
    if (!stickToBottom.current) return;
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, status, pendingSymptoms]);

  function onScroll() {
    const node = scroller.current;
    if (!node) return;
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
    stickToBottom.current = nearBottom;
    setShowJump(!nearBottom && node.scrollHeight > node.clientHeight + 120);
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
    <div className="flex h-dvh min-h-0 overflow-hidden bg-[#eaf4fb]">
      <ChatSidebar />
      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-sky-100 bg-white px-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              className="hidden min-h-11 min-w-11 place-items-center rounded-xl text-slate-600 hover:bg-teal-50 lg:grid"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <PanelLeft size={18} />
            </button>
            <button
              type="button"
              className="grid min-h-11 min-w-11 place-items-center rounded-xl text-slate-600 hover:bg-teal-50 lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open chats"
            >
              <Menu size={18} />
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-extrabold text-slate-900">Symptom conversation</p>
              <p className="hidden truncate text-xs text-slate-500 sm:block">Matches, urgency, sources, and nearby hospitals. Not a diagnosis.</p>
            </div>
          </div>
          <EmergencyCallButton urgent={urgent} />
        </header>
        <div className="relative min-h-0 flex-1">
          <div ref={scroller} onScroll={onScroll} className="absolute inset-0 overflow-x-hidden overflow-y-auto px-3 py-5 pb-16 sm:px-4">
            <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-5">
              {messagesLoading ? <Spinner label="Loading conversation..." /> : null}
              {!messagesLoading && !messages.length && !pendingSymptoms ? (
                <div className="m-auto w-full max-w-xl px-2 py-6 text-center">
                  <h2 className="text-xl font-extrabold text-slate-900">Tap where it hurts</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    Click a body region, then choose symptoms. You can also type in your own words. This is not a diagnosis.
                  </p>
                  <div className="mt-5 rounded-3xl border border-sky-200 bg-sky-50 px-4 py-5 shadow-sm">
                    <BodyFigure
                      view="front"
                      selected={[]}
                      focused={null}
                      onToggle={(region: BodyRegion) => composerRef.current?.openMap(region)}
                    />
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {REGION_ORDER.map((id) => (
                        <button
                          key={id}
                          type="button"
                          className="min-h-11 rounded-full border border-sky-300 bg-white px-3 text-xs font-bold text-sky-900 hover:bg-sky-100"
                          onClick={() => composerRef.current?.openMap(id)}
                        >
                          {REGION_LABELS[id]}
                        </button>
                      ))}
                    </div>
                  </div>
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
              {streaming && status ? (
                <p className="pl-12 text-sm font-semibold text-teal-800" aria-live="polite">
                  {status}
                </p>
              ) : null}
              {error ? (
                <div className="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3" role="alert">
                  <p className="text-sm font-semibold text-rose-800">{error}</p>
                  <Button variant="secondary" size="sm" className="mt-2" onClick={() => clearError()}>
                    Dismiss
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
          {showJump ? (
            <button
              type="button"
              className="absolute bottom-3 left-1/2 z-10 flex min-h-11 -translate-x-1/2 items-center gap-1 rounded-full border border-teal-100 bg-white px-3 text-xs font-bold text-teal-900 shadow-sm"
              onClick={() => {
                stickToBottom.current = true;
                scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
                setShowJump(false);
              }}
            >
              <ArrowDown size={14} /> Latest
            </button>
          ) : null}
        </div>
        <ChatInput ref={composerRef} disabled={sending || Boolean(pendingSymptoms)} streaming={streaming} error={error} onSend={handleSend} onStop={stopGeneration} />
      </section>
    </div>
  );
}
