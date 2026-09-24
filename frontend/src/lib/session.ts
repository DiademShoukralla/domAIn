const SESSION_KEY = "domain.chat.session_id";
const API_KEY_KEY = "domain.api_key";

export function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) {
    return existing;
  }
  const sessionId = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, sessionId);
  return sessionId;
}

export function getStoredApiKey(): string {
  return localStorage.getItem(API_KEY_KEY) ?? import.meta.env.VITE_API_KEY ?? "";
}

export function setStoredApiKey(apiKey: string): void {
  localStorage.setItem(API_KEY_KEY, apiKey.trim());
}

export function clearStoredApiKey(): void {
  localStorage.removeItem(API_KEY_KEY);
}
