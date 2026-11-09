/**
 * API client — all requests to the TrustVault backend.
 * Uses in-memory token (never localStorage).
 */
import { getMemoryToken } from "@/contexts/AuthContext";

const API_BASE = "/api/v1";

export class AppError extends Error {
  constructor(
    public readonly status: number,
    public readonly userMessage: string,
    public readonly correlationId?: string
  ) {
    super(userMessage);
    this.name = "AppError";
  }
}

async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; formData?: FormData; signal?: AbortSignal } = {}
): Promise<T> {
  const token = getMemoryToken();
  if (!token) throw new AppError(401, "Not authenticated");

  const correlationId = crypto.randomUUID();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Correlation-ID": correlationId,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: options.formData
      ? options.formData
      : options.body !== undefined
        ? JSON.stringify(options.body)
        : undefined,
    signal: options.signal,
    credentials: "same-origin",
  });

  if (!response.ok) {
    const serverCorrelationId = response.headers.get("X-Correlation-ID") ?? correlationId;
    let detail: string | undefined;
    try { detail = ((await response.json()) as { detail?: string }).detail; } catch { /* ignore */ }
    throw new AppError(response.status, _userMessage(response.status), serverCorrelationId);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function _userMessage(status: number): string {
  switch (status) {
    case 400: return "Invalid request. Please check your input.";
    case 401: return "You are not authenticated. Please log in.";
    case 403: return "You do not have permission to perform this action.";
    case 404: return "The requested resource was not found.";
    case 409: return "A conflict occurred. The resource may already exist.";
    case 413: return "The file is too large to upload.";
    case 422: return "Invalid data submitted. Please check the form.";
    case 429: return "Too many requests. Please slow down.";
    case 503: return "Service temporarily unavailable. Please try again shortly.";
    default:  return "An unexpected error occurred.";
  }
}

export const api = {
  get:    <T>(path: string, signal?: AbortSignal) => request<T>("GET", path, { signal }),
  post:   <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  put:    <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch:  <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  delete: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, formData: FormData) => request<T>("POST", path, { formData }),
};

// For direct fetch (downloads) — export token getter
export { getMemoryToken };
