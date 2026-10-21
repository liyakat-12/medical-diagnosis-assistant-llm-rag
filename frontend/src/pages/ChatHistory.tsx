import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Menu, PanelLeft } from "lucide-react";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { EmptyState, Spinner } from "../components/common/Spinner";
import { useChat } from "../context/ChatContext";
import { useApp } from "../context/AppContext";
import { groupChats } from "../utils/dates";

export function ChatHistory() {
  const { chats, chatsLoading, loadChats, error } = useChat();
  const { setSidebarOpen, sidebarCollapsed, setSidebarCollapsed } = useApp();
  useEffect(() => {
    void loadChats();
  }, [loadChats]);
  const groups = groupChats(chats);

  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-[#eaf4fb]">
      <ChatSidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-teal-100 bg-white px-3 sm:px-4">
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
          <p className="text-sm font-extrabold text-slate-900">Conversation history</p>
        </header>
        <main className="mx-auto w-full min-h-0 max-w-3xl flex-1 overflow-y-auto px-4 py-10">
          <h1 className="text-3xl font-extrabold text-slate-900">Conversation history</h1>
          <p className="mt-2 text-sm text-slate-600">Open a previous discussion. Answers are stored and are not regenerated.</p>
          {error ? <p className="mt-4 text-sm font-semibold text-rose-700">{error}</p> : null}
          {chatsLoading ? <Spinner className="mt-8" label="Loading conversations..." /> : null}
          {!chatsLoading && !chats.length ? (
            <div className="mt-8">
              <EmptyState title="Your conversations will appear here." body="Start a new chat to describe symptoms and save the exchange." />
            </div>
          ) : null}
          <div className="mt-8 space-y-6">
            {groups.map((group) => (
              <section key={group.label}>
                <h2 className="text-xs font-extrabold uppercase tracking-[0.16em] text-slate-400">{group.label}</h2>
                <ul className="mt-2 space-y-2">
                  {group.chats.map((chat) => (
                    <li key={chat.id}>
                      <Link to={`/chat/${chat.id}`} className="block rounded-2xl border border-teal-100 bg-white px-4 py-3 hover:bg-teal-50">
                        <p className="break-anywhere font-bold text-slate-900">{chat.title}</p>
                        <p className="text-xs text-slate-500">{chat.message_count} messages</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
