import type { Chat } from "../types";

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export type ChatGroup = { label: string; chats: Chat[] };

export function groupChats(chats: Chat[]): ChatGroup[] {
  const now = startOfDay(new Date());
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const week = new Date(now);
  week.setDate(now.getDate() - 7);

  const buckets: Record<string, Chat[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const chat of chats) {
    const raw = chat.last_message_at || chat.updated_at || chat.created_at;
    const stamp = raw ? startOfDay(new Date(raw)) : now;
    if (stamp.getTime() === now.getTime()) buckets.Today.push(chat);
    else if (stamp.getTime() === yesterday.getTime()) buckets.Yesterday.push(chat);
    else if (stamp >= week) buckets["Previous 7 days"].push(chat);
    else buckets.Older.push(chat);
  }

  return Object.entries(buckets)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, chats: items }));
}
