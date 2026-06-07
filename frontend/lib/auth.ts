export type AuthRole = "analyst" | "admin" | "owner";

export interface AuthSession {
  user_id: string;
  full_name: string;
  work_email: string;
  organization: string;
  role: AuthRole;
  session_token: string;
  expires_in_seconds: number;
  message: string;
}

const AUTH_SESSION_KEY = "cred-ible:auth-session:v1";
const AUTH_TOKEN_KEY = "cred-ible:session-token:v1";

function setSessionStorageValue(key: string, value: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    window.sessionStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function getSessionStorageValue(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function removeSessionStorageValue(key: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    return;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAuthSession(value: unknown): value is AuthSession {
  if (!isRecord(value)) return false;
  return (
    typeof value.user_id === "string" &&
    typeof value.full_name === "string" &&
    typeof value.work_email === "string" &&
    typeof value.organization === "string" &&
    (value.role === "analyst" || value.role === "admin" || value.role === "owner") &&
    typeof value.session_token === "string" &&
    typeof value.expires_in_seconds === "number" &&
    typeof value.message === "string"
  );
}

export function saveAuthSession(session: AuthSession): boolean {
  const ok = setSessionStorageValue(AUTH_SESSION_KEY, JSON.stringify(session));
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AUTH_TOKEN_KEY, session.session_token);
    }
  } catch {
    // ignore localStorage errors
  }
  return ok;
}

export function loadAuthSession(): AuthSession | null {
  const raw = getSessionStorageValue(AUTH_SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    return isAuthSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function clearAuthSession(): void {
  removeSessionStorageValue(AUTH_SESSION_KEY);
}

export function saveSessionToken(token: string): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    }
  } catch {
    // ignore
  }
}

export function loadSessionToken(): string | null {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function clearSessionToken(): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {
    // ignore
  }
}
