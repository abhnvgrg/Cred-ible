const DEFAULT_API_BASE_URL = "https://cred-ible.onrender.com";

export function getApiBaseUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
  return baseUrl.replace(/\/+$/, "");
}

export const API_BASE_URL = getApiBaseUrl();
