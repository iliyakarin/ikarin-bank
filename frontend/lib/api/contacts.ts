import { z } from "zod";
import { api } from "./client";

/**
 * Contacts API Service
 */

export const ContactResponseSchema = z.object({
  id: z.number(),
  user_id: z.number().optional(),
  contact_name: z.string(),
  contact_email: z.string().nullable().optional(),
  contact_type: z.string(),
  merchant_id: z.string().nullable().optional(),
  subscriber_id: z.string().nullable().optional(),
  bank_name: z.string().nullable().optional(),
  routing_number: z.string().nullable().optional(),
  account_number: z.string().nullable().optional(),
});

// Normalized shape used across the UI
export const ContactSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string().optional(),
  contact_type: z.string(),
  merchant_id: z.string().nullable().optional(),
  subscriber_id: z.string().nullable().optional(),
});

export type Contact = z.infer<typeof ContactSchema>;

export async function getContacts(): Promise<Contact[]> {
  const raw = await api.get<z.infer<typeof ContactResponseSchema>[]>("/api/v1/contacts", {
    schema: z.array(ContactResponseSchema)
  });
  // Map backend field names to the normalized UI shape
  return raw
    .filter(c => c.contact_email) // only contacts with an email are useful for transfers
    .map(c => ({
      id: c.id,
      email: c.contact_email!,
      name: c.contact_name,
      contact_type: c.contact_type,
      merchant_id: c.merchant_id ?? undefined,
      subscriber_id: c.subscriber_id ?? undefined,
    }));
}


export async function getVendors(): Promise<{ vendors: any[] }> {
  return api.get<{ vendors: any[] }>("/api/v1/vendors");
}
