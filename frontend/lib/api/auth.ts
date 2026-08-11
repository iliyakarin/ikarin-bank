import { z } from "zod";
import { api } from "./client";

/**
 * Auth API Service
 */

export const UserSchema = z.object({
  id: z.number(),
  first_name: z.string().nullable().optional(),
  last_name: z.string().nullable().optional(),
  email: z.string(),
  backup_email: z.string().optional().nullable(),
  role: z.string(),
  time_format: z.string().optional(),
  date_format: z.string().optional(),
});

export type User = z.infer<typeof UserSchema>;

export async function getCurrentUser(): Promise<User> {
  return api.get<User>("/api/v1/me", {
    schema: UserSchema
  });
}

export async function logout(): Promise<{ status: string }> {
  return api.post<{ status: string }>("/api/v1/logout", {});
}

export async function renewToken(): Promise<{ access_token: string }> {
  // retry: false — a 401 here means the session is already gone, and the
  // client's 401 handler would otherwise recurse back into this call.
  return api.post<{ access_token: string }>("/api/v1/token/renew", {}, { retry: false });
}

export async function updatePreferences(preferences: {
  time_format: "12h" | "24h";
  date_format: "EU" | "US";
}): Promise<{ status: string }> {
  return api.patch<{ status: string }>("/api/v1/users/me/preferences", preferences);
}
