const TOKEN_KEY = "pdf-rag-access-token";
export const AUTH_CLEARED_EVENT = "pdf-rag-auth-cleared";

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_CLEARED_EVENT));
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

