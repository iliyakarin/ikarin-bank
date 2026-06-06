import { z } from "zod";

/**
 * Base API Client for Karin Bank
 * Handles authorization, consistent error parsing, Zod validation,
 * token refresh on 401, and retry logic for transient failures.
 */

const BASE_URL = "";
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 500;

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public detail?: any,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class NetworkError extends Error {
  constructor(public original: Error) {
    super(`Network error: ${original.message}`);
    this.name = "NetworkError";
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("bank_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function refreshAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const refreshToken = localStorage.getItem("bank_refresh_token");
  if (!refreshToken) return null;
  try {
    const resp = await fetch(`${BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.access_token) {
      localStorage.setItem("bank_token", data.access_token);
      return data.access_token;
    }
  } catch {
    /* ignore */
  }
  return null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  schema?: z.ZodTypeAny;
  retry?: boolean;
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, schema, retry = true, ...fetchOptions } = options;

  let url = `${BASE_URL}${path}`;
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const authHeaders = await getAuthHeaders();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders,
    ...(fetchOptions.headers as Record<string, string>),
  };

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers,
      });

      if (!response.ok) {
        if (response.status === 401 && attempt === 0 && retry) {
          const newToken = await refreshAuthToken();
          if (newToken) {
            headers["Authorization"] = `Bearer ${newToken}`;
            continue;
          }
          localStorage.removeItem("bank_token");
          localStorage.removeItem("bank_refresh_token");
          if (typeof window !== "undefined") {
            window.location.href = "/auth/login";
          }
        }

        let errorDetail: any;
        try {
          errorDetail = await response.json();
        } catch {
          errorDetail = await response.text();
        }

        const detailObj =
          typeof errorDetail === "object" ? errorDetail : {};
        throw new ApiError(
          response.status,
          `API Error: ${response.statusText}`,
          errorDetail,
          detailObj.code || detailObj.detail,
        );
      }

      const data = await response.json();

      if (schema) {
        const result = schema.safeParse(data);
        if (!result.success) {
          console.error("Zod Validation Failed:", result.error);
        }
      }

      return data as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;

      lastError = err instanceof Error ? err : new Error(String(err));

      if (retry && attempt < MAX_RETRIES) {
        await sleep(RETRY_DELAY_MS * (attempt + 1));
      }
    }
  }

  throw lastError
    ? new NetworkError(lastError)
    : new NetworkError(new Error("Unknown network error"));
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(
    path: string,
    body?: any,
    options?: RequestOptions,
  ) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    }),
  put: <T>(path: string, body?: any, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: any, options?: RequestOptions) =>
    request<T>(path, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
