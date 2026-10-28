import { useEffect, useMemo, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, MessageSquarePlus, PanelLeft, Pencil, Search, Stethoscope, Trash2, UserRound, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useChat } from "../../context/ChatContext";
import { SIDEBAR_RAIL, useApp } from "../../context/AppContext";
import { groupChats } from "../../utils/dates";
import { Button } from "../common/Button";
import { Modal } from "../common/Spinner";
import { cn } from "../../lib/cn";

export function ChatSidebar() {
  const { user, logout } = useAuth();
  const { chats, chatsLoading, activeChatId, startNewChat, renameChat, removeChat } = useChat();
  const { sidebarOpen, setSidebarOpen, sidebarCollapsed, setSidebarCollapsed, sidebarWidth, setSidebarWidth } = useApp();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return chats;
    return chats.filter((chat) => chat.title.toLowerCase().includes(needle));
  }, [chats, query]);
  const groups = useMemo(() => groupChats(filtered), [filtered]);
  const deleteTarget = chats.find((chat) => chat.id === deleteId);

  useEffect(() => {
    if (!sidebarOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setSidebarOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sidebarOpen, setSidebarOpen]);

  function onResizePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.pointerType === "touch" || sidebarCollapsed) return;
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = sidebarWidth;
    function onMove(moveEvent: PointerEvent) {
      setSidebarWidth(startWidth + (moveEvent.clientX - startX));
    }
    function onUp() {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  }

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
          "relative z-50 flex h-full w-72 shrink-0 flex-col border-r border-teal-100 bg-[#eef5f3] lg:w-[var(--sidebar-w)]",
          "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:shadow-2xl max-lg:transition-transform max-lg:duration-200",
          !sidebarOpen && "max-lg:-translate-x-full",
        )}
        style={{ ["--sidebar-w" as string]: `${sidebarCollapsed ? SIDEBAR_RAIL : sidebarWidth}px` }}
        aria-label="Conversation history"
      >
        <div className={cn("flex items-center gap-2 px-3 py-3", sidebarCollapsed ? "justify-center" : "justify-between")}>
          <Link to="/" className="flex min-w-0 items-center gap-2 font-extrabold text-teal-900" title="MediAssist home">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-teal-700 text-white">
              <Stethoscope size={18} />
            </span>
            {sidebarCollapsed ? <span className="sr-only">MediAssist</span> : <span className="truncate">MediAssist</span>}
          </Link>
          {sidebarCollapsed ? null : (
            <button className="min-h-11 min-w-11 rounded-xl text-slate-500 hover:bg-white lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar">
              <X size={18} className="mx-auto" />
            </button>
          )}
        </div>
        <div className="px-3">
          <Button
            className={cn("w-full", sidebarCollapsed && "h-11 w-11 px-0")}
            onClick={() => void startNewChat()}
            aria-label="New chat"
            title="New chat"
          >
            <MessageSquarePlus size={16} />
            {sidebarCollapsed ? null : "New chat"}
          </Button>
          {sidebarCollapsed ? (
            <button
              type="button"
              className="mt-3 grid h-11 w-full place-items-center rounded-xl text-slate-600 hover:bg-white"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <PanelLeft size={18} />
            </button>
          ) : (
            <label className="mt-3 flex min-h-11 items-center gap-2 rounded-2xl border border-teal-100 bg-white px-3">
              <Search size={16} className="shrink-0 text-slate-400" />
              <input
                className="w-full min-w-0 bg-transparent text-sm outline-none"
                placeholder="Search chats"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                aria-label="Search chats"
              />
            </label>
          )}
        </div>
        {sidebarCollapsed ? (
          <div className="mt-4 flex-1" />
        ) : (
          <div className="mt-4 min-h-0 flex-1 overflow-y-auto px-3 pb-4">
            {chatsLoading ? <p className="px-2 text-sm text-slate-500">Loading conversations...</p> : null}
            {!chatsLoading && !filtered.length ? (
              <p className="px-2 text-sm leading-6 text-slate-500">{query ? "No conversations match that search." : "Your conversations will appear here."}</p>
            ) : null}
            {groups.map((group) => (
              <section key={group.label} className="mb-4">
                <h2 className="px-2 pb-1 text-[11px] font-extrabold uppercase tracking-[0.16em] text-slate-400">{group.label}</h2>
                <ul className="space-y-1">
                  {group.chats.map((chat) => (
                    <li key={chat.id}>
                      <div
                        className={cn(
                          "group flex items-center rounded-2xl px-2 py-1.5",
                          activeChatId === chat.id ? "bg-white shadow-sm ring-1 ring-teal-100" : "hover:bg-white/80",
                        )}
                      >
                        <button
                          className="min-h-11 min-w-0 flex-1 py-1 text-left text-sm font-bold text-slate-800"
                          onClick={() => {
                            setSidebarOpen(false);
                            navigate(`/chat/${chat.id}`);
                          }}
                        >
                          <span className="line-clamp-2 break-anywhere">{chat.title}</span>
                        </button>
                        <button
                          type="button"
                          className="min-h-11 min-w-11 rounded-lg text-slate-400 hover:text-teal-800 focus-visible:opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus:opacity-100"
                          aria-label={`Rename ${chat.title}`}
                          title="Rename"
                          onClick={() => {
                            setRenameId(chat.id);
                            setTitle(chat.title);
                          }}
                        >
                          <Pencil size={14} className="mx-auto" />
                        </button>
                        <button
                          type="button"
                          className="min-h-11 min-w-11 rounded-lg text-slate-400 hover:text-rose-700 focus-visible:opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:focus:opacity-100"
                          aria-label={`Delete ${chat.title}`}
                          title="Delete"
                          onClick={() => setDeleteId(chat.id)}
                        >
                          <Trash2 size={14} className="mx-auto" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
        <div className={cn("border-t border-teal-100 p-3", sidebarCollapsed && "px-2")}>
          {sidebarCollapsed ? (
            <div className="flex flex-col items-center gap-2">
              <button type="button" className="grid h-11 w-11 place-items-center rounded-xl hover:bg-white" aria-label="Profile" title="Profile" onClick={() => navigate("/profile")}>
                <UserRound size={18} />
              </button>
              <button type="button" className="grid h-11 w-11 place-items-center rounded-xl hover:bg-white" aria-label="Logout" title="Logout" onClick={() => void logout()}>
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <>
              <p className="truncate text-sm font-bold text-slate-800">{user?.name}</p>
              <div className="mt-2 flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => navigate("/profile")}>
                  Profile
                </Button>
                <Button variant="ghost" size="sm" onClick={() => void logout()}>
                  <LogOut size={14} /> Logout
                </Button>
              </div>
            </>
          )}
        </div>
        {sidebarCollapsed ? null : (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize sidebar"
            title="Drag to resize"
            className="absolute inset-y-0 right-0 hidden w-1.5 cursor-col-resize bg-transparent hover:bg-teal-300/80 lg:block"
            onPointerDown={onResizePointerDown}
          />
        )}
        <Modal open={Boolean(renameId)} title="Rename conversation" onClose={() => setRenameId(null)}>
          <input className="w-full rounded-2xl border border-teal-100 px-3 py-2 text-sm" value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Chat title" />
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
        <Modal open={Boolean(deleteId)} title="Delete conversation?" onClose={() => setDeleteId(null)}>
          <p className="text-sm leading-6 text-slate-600">This removes “{deleteTarget?.title || "this chat"}” and its messages from your account. This cannot be undone.</p>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (deleteId) void removeChat(deleteId);
                setDeleteId(null);
              }}
            >
              Delete
            </Button>
          </div>
        </Modal>
      </aside>
    </>
  );
}
