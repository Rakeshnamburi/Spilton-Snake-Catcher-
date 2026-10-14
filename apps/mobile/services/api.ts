import * as SecureStore from "expo-secure-store";
import type {IncidentMedia, Paginated} from "@/features/incidents/types";
import type {SelectedMedia} from "@/features/report/types";

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SESSION_KEY = "spilton_session";
const DEFAULT_TIMEOUT_MS = 15_000;

type StructuredError = {
  error?: {code?: string; message?: string; details?: unknown};
  detail?: string | Array<{msg?: string}>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code = "REQUEST_FAILED",
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiRequestInit = RequestInit & {timeoutMs?: number};

function errorMessage(body: StructuredError) {
  if (body.error?.message) return body.error.message;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map(item => item.msg).filter(Boolean).join(" ");
  return "Request failed";
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(SESSION_KEY);
}

export async function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  let token: string | null;
  try {
    token = await getAccessToken();
  } catch {
    throw new ApiError("Secure session storage is unavailable on this device.", 0, "SESSION_STORAGE_ERROR");
  }
  const {timeoutMs, ...requestInit} = init;
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isForm && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const controller = init.signal ? undefined : new AbortController();
  const timeout = controller
    ? setTimeout(() => controller.abort(), timeoutMs ?? DEFAULT_TIMEOUT_MS)
    : undefined;
  try {
    const response = await fetch(resolveApiUrl(path), {
      ...requestInit,
      // Native clients authenticate only with the SecureStore bearer token.
      // Ignoring cookies prevents a server-set web session from surviving sign-out.
      credentials: "omit",
      headers,
      signal: init.signal ?? controller?.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as StructuredError;
      if (response.status === 401) await clearToken().catch(() => undefined);
      throw new ApiError(
        errorMessage(body),
        response.status,
        body.error?.code ?? (response.status === 401 ? "SESSION_EXPIRED" : "REQUEST_FAILED"),
        body.error?.details,
      );
    }
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("The server took too long to respond.", 0, "TIMEOUT");
    }
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0, "NETWORK_ERROR");
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}

export async function uploadIncidentMedia(incidentId: string, media: SelectedMedia) {
  const body = new FormData();
  body.append("file", {
    uri: media.uri,
    name: media.fileName,
    type: media.mimeType,
  } as unknown as Blob);
  return api<IncidentMedia>(`/api/v1/incidents/${incidentId}/media`, {
    method: "POST",
    body,
    timeoutMs: 30_000,
  });
}

export function resolveApiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function normalizePage<T>(value: Paginated<T> | T[]): Paginated<T> {
  if (Array.isArray(value)) {
    return {items: value, total: value.length, page: 1, page_size: value.length, pages: 1};
  }
  return value;
}

export async function saveToken(token: string) {
  await SecureStore.setItemAsync(SESSION_KEY, token, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function clearToken() {
  await SecureStore.deleteItemAsync(SESSION_KEY);
}
