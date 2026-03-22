import { z } from "zod";
import { api } from "./client";

/**
 * Deposits API Service
 * Standardized with Zod validation and unified client.
 */

export const PaymentIntentResponseSchema = z.object({
  client_secret: z.string(),
  id: z.string().optional(),
});

export type PaymentIntentResponse = z.infer<typeof PaymentIntentResponseSchema>;

export const SubscriptionSchema = z.object({
  active: z.boolean(),
  plan_name: z.string().optional(),
  amount: z.number().optional(),
  current_period_end: z.string().optional(),
  status: z.string().optional(),
});

export type UserSubscription = z.infer<typeof SubscriptionSchema>;

export async function createPaymentIntent(amount: number): Promise<PaymentIntentResponse> {
  return api.post<PaymentIntentResponse>("/api/v1/deposits/create-payment-intent", { amount }, {
    schema: PaymentIntentResponseSchema
  });
}

export async function fulfillPayment(paymentIntentId: string): Promise<{ status: string }> {
  return api.post<{ status: string }>("/api/v1/deposits/fulfill", { payment_intent_id: paymentIntentId });
}

export async function createCheckoutSession(payload: {
  amount: number;
  currency: string;
  mode: "payment" | "subscription";
  success_url: string;
  cancel_url: string;
}): Promise<{ id: string; url: string }> {
  return api.post<{ id: string; url: string }>("/api/v1/deposits/create-checkout-session", payload);
}

export async function createPortalSession(return_url: string): Promise<{ url: string }> {
  return api.post<{ url: string }>("/api/v1/deposits/create-portal-session", { return_url });
}

export async function getSubscriptionStatus(): Promise<UserSubscription> {
  return api.get<UserSubscription>("/api/v1/deposits/subscriptions/me", {
    schema: SubscriptionSchema
  });
}
