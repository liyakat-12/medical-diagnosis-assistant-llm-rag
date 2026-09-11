import type { Chat, ChatMessage, StreamEvent } from "../types";
import { apiFetch, readSse } from "./api";

export function listChats(query?: string): Promise<Chat[]> {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
  return apiFetch<Chat[]>(`/chats${suffix}`);
}

export function createChat(title?: string): Promise<Chat> {
  return apiFetch<Chat>("/chats", {
    method: "POST",
    body: JSON.stringify({ title: title || null }),
  });
}

export function getChat(chatId: string): Promise<Chat> {
  return apiFetch<Chat>(`/chats/${chatId}`);
}

export function updateChat(chatId: string, fields: { title?: string; archived?: boolean }): Promise<Chat> {
  return apiFetch<Chat>(`/chats/${chatId}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export function deleteChat(chatId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/chats/${chatId}`, { method: "DELETE" });
}

export function listMessages(chatId: string): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(`/chats/${chatId}/messages`);
}

export function streamMessage(
  chatId: string,
  content: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return readSse(`/chats/${chatId}/messages/stream`, { content }, (raw) => onEvent(raw as unknown as StreamEvent), signal);
}
