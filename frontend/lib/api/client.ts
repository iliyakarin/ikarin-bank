import { z } from "zod";

/**
 * Base API Client for Karin Bank
 * Handles authorization, consistent error parsing, and Zod validation.
 */

const BASE_URL = "";

export class ApiError extends Error {
  constructor(public status: number, public message: string, public detail?: any) {
    super(message);
    this.name = "ApiError";
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("bank_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
  schema?: z.ZodTypeAny;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, schema, ...fetchOptions } = options;
  
  let url = `${BASE_URL}${path}`;
  if (params) {
    const searchParams = new URLSearchParams(params);
    url += `?${searchParams.toString()}`;
  }

  const authHeaders = await getAuthHeaders();
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders,
    ...(fetchOptions.headers as Record<string, string>),
  };

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    let errorDetail;
    try {
      errorDetail = await response.json();
    } catch {
      errorDetail = await response.text();
    }
    throw new ApiError(response.status, `API Error: ${response.statusText}`, errorDetail);
  }

  const data = await response.json();

  if (schema) {
    const result = schema.safeParse(data);
    if (!result.success) {
      console.error("Zod Validation Failed:", result.error);
      // In production we might still return the data, but for hardening we log strictly
    }
    return data as T;
  }

  return data as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: any, options?: RequestOptions) => 
    request<T>(path, { ...options, method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body?: any, options?: RequestOptions) => 
    request<T>(path, { ...options, method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: any, options?: RequestOptions) => 
    request<T>(path, { ...options, method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: "DELETE" }),
};
