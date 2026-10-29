import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, MapPin, Menu, PanelLeft } from "lucide-react";
import { useParams, useSearchParams } from "react-router-dom";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { ChatInput, type BodySelection, type ChatInputHandle } from "../components/chat/ChatInput";
import { BodyMapCard } from "../components/bodymap/BodyMap";
import { type BodyRegion } from "../utils/bodyMap";
import { MessageBubble } from "../components/chat/MessageBubble";
import { formatFollowUpQuery, type FollowUpAnswers } from "../components/chat/FollowUpCard";
import { EmergencyCallButton } from "../components/chat/EmergencyCallButton";
import { Spinner } from "../components/common/Spinner";
import { Button } from "../components/common/Button";
import { useChat } from "../context/ChatContext";
import { useApp } from "../context/AppContext";
import { isIncompleteMessage } from "../utils/chatSession";
import { conversationChrome } from "../utils/conversationChrome";
import { looksEmergency, needsPromptAssessment } from "../utils/emergency";
import { needsSymptomIntake } from "../utils/intent";

const HospitalFinderModal = lazy(() =>
  import("../components/hospitals/HospitalFinderModal").then((mod) => ({ default: mod.HospitalFinderModal })),
);
const SymptomIntakeModal = lazy(() =>
  import("../components/modals/SymptomIntakeModal").then((mod) => ({ default: mod.SymptomIntakeModal })),
);

export function Chat() {
  const { chatId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { loadChats, openChat, showBlankChat, activeChatId, messages, messagesLoading, sendMessage, stopGeneration, retryLast, sending, streaming, status, error, clearError } = useChat();
  const { setSidebarOpen, sidebarCollapsed, setSidebarCollapsed } = useApp();
  const composerRef = useRef<ChatInputHandle>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const lastChatId = useRef<string | undefined>(undefined);
  const lastFocusedUser = useRef<string | null>(null);
  const [pendingSymptoms, setPendingSymptoms] = useState<string | null>(null);
  const pendingRegions = useRef<BodyRegion[]>([]);
  const [bodySelection, setBodySelection] = useState<BodySelection>({ regions: [], view: "front" });
  const [hospitalsOpen, setHospitalsOpen] = useState(false);
  const [showJump, setShowJump] = useState(false);

  useEffect(() => {
    void loadChats();
  }, [loadChats]);

  useEffect(() => {
    if (searchParams.get("map") !== "1") return;
    composerRef.current?.openMap();
    const next = new URLSearchParams(searchParams);
    next.delete("map");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (chatId) {
      if (chatId === activeChatId && (sending || streaming)) return;
      void openChat(chatId);
    } else if (!sending && !streaming) {
      showBlankChat();
    }
    if (lastChatId.current !== chatId) {
      setPendingSymptoms(null);
      lastChatId.current = chatId;
    }
  }, [chatId, activeChatId, sending, streaming, openChat, showBlankChat]);

  useEffect(() => {
    let lastUser: (typeof messages)[number] | undefined;
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      if (messages[index].role === "user") {
        lastUser = messages[index];
        break;
      }
    }
    if (lastUser && lastUser.id !== lastFocusedUser.current) {
      lastFocusedUser.current = lastUser.id;
      stickToBottom.current = true;
      document.getElementById(`msg-${lastUser.id}`)?.scrollIntoView({ behavior: streaming ? "auto" : "smooth", block: "start" });
      return;
    }
    if (!stickToBottom.current) return;
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: streaming ? "auto" : "smooth" });
  }, [messages, status, pendingSymptoms, streaming]);

  function onScroll() {
    const node = scroller.current;
    if (!node) return;
    const nearBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
    stickToBottom.current = nearBottom;
    setShowJump(!nearBottom && node.scrollHeight > node.clientHeight + 120);
  }

  const handleSend = useCallback(
    (value: string) => {
      const bodyRegions = composerRef.current?.sentBodyRegions() ?? [];
      pendingRegions.current = bodyRegions;
        if (looksEmergency(value, messages) || needsPromptAssessment(value) || !needsSymptomIntake(value, messages)) {
        setPendingSymptoms(null);
        void sendMessage(value, { bodyRegions });
        return;
      }
      setPendingSymptoms(value);
    },
    [messages, sendMessage],
  );

  const handleFollowUp = useCallback(
    (answers: FollowUpAnswers) => {
      if (!pendingSymptoms) return;
      const query = formatFollowUpQuery(pendingSymptoms, answers);
      setPendingSymptoms(null);
      void sendMessage(query, { bodyRegions: pendingRegions.current });
    },
    [pendingSymptoms, sendMessage],
  );

  const openHospitals = useCallback(() => setHospitalsOpen(true), []);

  const chrome = useMemo(() => conversationChrome(messages), [messages]);
  const urgent = chrome.emphasizeEmergency;
  const lastIncomplete = Boolean(messages.at(-1) && isIncompleteMessage(messages.at(-1)!));
  const showRetry = Boolean(error) || lastIncomplete;

  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-[#eaf4fb]">
      <ChatSidebar />
      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-2 overflow-hidden border-b border-sky-100 bg-white px-2 sm:gap-3 sm:px-4">
          <div className="flex min-w-0 items-center gap-1 sm:gap-2">
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
              <p className="truncate text-sm font-extrabold text-slate-900">{chrome.title}</p>
              <p className="hidden truncate text-xs text-slate-500 sm:block">{chrome.subtitle}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <button
              type="button"
              onClick={openHospitals}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-teal-200 bg-white px-2.5 text-xs font-extrabold text-teal-900 hover:bg-teal-50 sm:px-3"
            >
              <MapPin size={14} />
              <span className="sm:hidden">Hospitals</span>
              <span className="hidden sm:inline">Nearby hospitals</span>
            </button>
            <EmergencyCallButton urgent={urgent} />
          </div>
        </header>
        <div className="relative min-h-0 flex-1">
          <div ref={scroller} onScroll={onScroll} className="absolute inset-0 overflow-x-hidden overflow-y-auto px-3 py-5 pb-28 sm:px-4">
            <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-5">
              {messagesLoading ? <Spinner label="Loading conversation..." /> : null}
              {!messagesLoading && !messages.length && !pendingSymptoms ? (
                <div className="m-auto w-full max-w-3xl py-4">
                  <BodyMapCard
                    view={bodySelection.view}
                    onViewChange={(view) => composerRef.current?.setView(view)}
                    selectedRegions={bodySelection.regions}
                    onToggleRegion={(region: BodyRegion) => composerRef.current?.toggleRegion(region)}
                    onClear={() => composerRef.current?.clearRegions()}
                    onDescribe={() => composerRef.current?.openMap()}
                    disabled={sending}
                  />
                </div>
              ) : null}
              {messages.map((message) => (
                <div key={message.id} id={`msg-${message.id}`}>
                  <MessageBubble
                    message={message}
                    status={message.streaming ? status : undefined}
                    onOpenHospitals={openHospitals}
                  />
                </div>
              ))}
              {showRetry ? (
                <div className="rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3" role="alert" aria-live="assertive">
                  <p className="text-sm font-semibold text-rose-800">{error || "This reply was stopped before it finished."}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button variant="secondary" size="sm" onClick={() => void retryLast()}>
                      Try again
                    </Button>
                    {error ? (
                      <Button variant="secondary" size="sm" onClick={() => clearError()}>
                        Dismiss
                      </Button>
                    ) : null}
                  </div>
                </div>
              ) : null}
              {messages.length ? <div className="h-16 shrink-0" aria-hidden /> : null}
            </div>
          </div>
          {showJump ? (
            <button
              type="button"
              className="absolute bottom-5 right-4 z-10 flex min-h-11 items-center gap-1 rounded-full border border-teal-100 bg-white px-3 text-xs font-bold text-teal-900 shadow-sm sm:right-6"
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
        <ChatInput ref={composerRef} disabled={sending || Boolean(pendingSymptoms)} streaming={streaming} error={error} onSend={handleSend} onStop={stopGeneration} onSelectionChange={setBodySelection} />
      </section>
      {pendingSymptoms ? (
        <Suspense fallback={null}>
          <SymptomIntakeModal
            symptoms={pendingSymptoms}
            onContinue={handleFollowUp}
            onSkip={() => {
              const text = pendingSymptoms;
              setPendingSymptoms(null);
              void sendMessage(text, { bodyRegions: pendingRegions.current });
            }}
          />
        </Suspense>
      ) : null}
      {hospitalsOpen ? (
        <Suspense fallback={null}>
          <HospitalFinderModal open onClose={() => setHospitalsOpen(false)} />
        </Suspense>
      ) : null}
    </div>
  );
}
