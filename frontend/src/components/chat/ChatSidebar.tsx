import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, MessageSquarePlus, Pencil, Search, Stethoscope, Trash2, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useChat } from "../../context/ChatContext";
import { useApp } from "../../context/AppContext";
import { groupChats } from "../../utils/dates";
import { Button } from "../common/Button";
import { Modal } from "../common/Spinner";
import { cn } from "../../lib/cn";

export function ChatSidebar() {
  const { user, logout } = useAuth();
  const { chats, chatsLoading, activeChatId, startNewChat, renameChat, removeChat } = useChat();
  const { sidebarOpen, setSidebarOpen } = useApp();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const filtered = chats.filter((chat) => chat.title.toLowerCase().includes(query.toLowerCase()));
  const groups = groupChats(filtered);

  return (
    <>
      {sidebarOpen ? (
        <button
          className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
          aria-label="Close sidebar overlay"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <aside
        className={cn(
          "z-50 flex h-full w-72 shrink-0 flex-col border-r border-teal-100 bg-[#e8f2ef] transition-transform duration-200",
          "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:shadow-2xl",
          !sidebarOpen && "max-lg:-translate-x-full",
        )}
      >
      <div className="flex items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2 font-extrabold text-teal-900">
          <Stethoscope size={18} /> MediAssist
        </Link>
        <button className="lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar">
          <X size={18} />
        </button>
      </div>
      <div className="px-3">
        <Button className="w-full" onClick={() => void startNewChat()}>
          <MessageSquarePlus size={16} /> New chat
        </Button>
        <label className="mt-3 flex items-center gap-2 rounded-2xl border border-teal-100 bg-white px-3 py-2">
          <Search size={16} className="text-slate-400" />
          <input
            className="w-full bg-transparent text-sm outline-none"
            placeholder="Search chats"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search chats"
          />
        </label>
      </div>
      <div className="mt-4 flex-1 overflow-y-auto px-3 pb-4">
        {chatsLoading ? <p className="px-2 text-sm text-slate-500">Loading conversations...</p> : null}
        {!chatsLoading && !filtered.length ? (
          <p className="px-2 text-sm text-slate-500">Your conversations will appear here.</p>
        ) : null}
        {groups.map((group) => (
          <section key={group.label} className="mb-4">
            <h2 className="px-2 pb-1 text-[11px] font-extrabold uppercase tracking-[0.16em] text-slate-400">{group.label}</h2>
            <ul className="space-y-1">
              {group.chats.map((chat) => (
                <li key={chat.id}>
                  <div
                    className={cn(
                      "group flex items-center rounded-2xl px-2 py-2",
                      activeChatId === chat.id ? "bg-white shadow-sm ring-1 ring-teal-100" : "hover:bg-white/80",
                    )}
                  >
                    <button
                      className="min-w-0 flex-1 text-left text-sm font-bold text-slate-800"
                      onClick={() => {
                        setSidebarOpen(false);
                        navigate(`/chat/${chat.id}`);
                      }}
                    >
                      <span className="line-clamp-2">{chat.title}</span>
                    </button>
                    <button
                      className="rounded-lg p-1 text-slate-400 opacity-0 hover:text-teal-800 group-hover:opacity-100 focus:opacity-100"
                      aria-label="Rename chat"
                      onClick={() => {
                        setRenameId(chat.id);
                        setTitle(chat.title);
                      }}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      className="rounded-lg p-1 text-slate-400 opacity-0 hover:text-rose-700 group-hover:opacity-100 focus:opacity-100"
                      aria-label="Delete chat"
                      onClick={() => void removeChat(chat.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <div className="border-t border-teal-100 p-4">
        <p className="text-sm font-bold text-slate-800">{user?.name}</p>
        <div className="mt-2 flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => navigate("/profile")}>
            Profile
          </Button>
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            <LogOut size={14} /> Logout
          </Button>
        </div>
      </div>
      <Modal
        open={Boolean(renameId)}
        title="Rename conversation"
        onClose={() => setRenameId(null)}
      >
        <input
          className="w-full rounded-2xl border border-teal-100 px-3 py-2 text-sm"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          aria-label="Chat title"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setRenameId(null)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (renameId && title.trim()) void renameChat(renameId, title.trim());
              setRenameId(null);
            }}
          >
            Save
          </Button>
        </div>
      </Modal>
      </aside>
    </>
  );
}
