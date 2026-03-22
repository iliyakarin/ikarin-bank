import { z } from "zod";
import { api } from "./client";

/**
 * Contacts API Service
 */

export const ContactSchema = z.object({
  id: z.number(),
  email: z.string(),
  name: z.string().optional(),
  contact_type: z.enum(["individual", "merchant"]),
  merchant_id: z.string().optional(),
  subscriber_id: z.string().optional(),
});

export type Contact = z.infer<typeof ContactSchema>;

export async function getContacts(): Promise<Contact[]> {
  return api.get<Contact[]>("/api/v1/contacts", {
    schema: z.array(ContactSchema)
  });
}

export async function getVendors(): Promise<{ vendors: any[] }> {
  return api.get<{ vendors: any[] }>("/api/v1/vendors");
}
