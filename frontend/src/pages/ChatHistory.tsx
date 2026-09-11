import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Navbar } from "../components/navbar/Navbar";
import { Footer } from "../components/footer/Footer";
import { ChatSidebar } from "../components/chat/ChatSidebar";
import { EmptyState, Spinner } from "../components/common/Spinner";
import { useChat } from "../context/ChatContext";
import { groupChats } from "../utils/dates";

export function ChatHistory() {
  const { chats, chatsLoading, loadChats } = useChat();
  useEffect(() => {
    void loadChats();
  }, [loadChats]);
  const groups = groupChats(chats);

  return (
    <div className="flex min-h-screen bg-[#f4f8f7]">
      <ChatSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar />
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-10">
          <h1 className="text-3xl font-extrabold text-slate-900">Conversation history</h1>
          <p className="mt-2 text-sm text-slate-600">Open a previous discussion. Answers are stored and are not regenerated.</p>
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
                        <p className="font-bold text-slate-900">{chat.title}</p>
                        <p className="text-xs text-slate-500">{chat.message_count} messages</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
}
