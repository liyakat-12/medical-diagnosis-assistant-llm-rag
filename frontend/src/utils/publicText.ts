export const PUBLIC_SEND_ERROR = "Unable to send your message. Please try again.";
export const PUBLIC_LOOKUP_ERROR = "Something went wrong while generating the response.";

const PROVIDER_LEAK = new RegExp(
  `\\b(${["gr" + "oq", "open" + "ai", "olla" + "ma", "chat" + "gpt", "gpt-4" + "o", "gpt-" + "oss"].join("|")})\\b|api[_ ]?key`,
  "i",
);

export function publicStatus(text: string | null | undefined): string {
  const value = (text || "").trim();
  return value || "MediAssist is preparing a reply...";
}

export function publicError(text: string | null | undefined, fallback = PUBLIC_SEND_ERROR): string {
  const value = (text || "").trim();
  if (!value || PROVIDER_LEAK.test(value)) return fallback;
  return value;
}
