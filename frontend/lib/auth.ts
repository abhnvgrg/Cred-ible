export type AuthRole = "analyst" | "admin";

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
    (value.role === "analyst" || value.role === "admin") &&
    typeof value.session_token === "string" &&
    typeof value.expires_in_seconds === "number" &&
    typeof value.message === "string"
  );
}

export function saveAuthSession(session: AuthSession): boolean {
  return setSessionStorageValue(AUTH_SESSION_KEY, JSON.stringify(session));
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
