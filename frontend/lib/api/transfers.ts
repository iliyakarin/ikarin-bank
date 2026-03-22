import { z } from "zod";
import { api } from "./client";

/**
 * Transfers API Service
 * Handles P2P, Scheduled, and Payment Requests.
 */

export const TransferResponseSchema = z.object({
  transaction_id: z.string(),
  status: z.string(),
});

export type TransferResponse = z.infer<typeof TransferResponseSchema>;

export const ScheduledPaymentSchema = z.object({
  id: z.number(),
  recipient_email: z.string(),
  amount: z.number(),
  frequency: z.string(),
  frequency_interval: z.string().optional(),
  start_date: z.string(),
  next_payment_date: z.string().optional(),
  status: z.string(),
});

export type ScheduledPayment = z.infer<typeof ScheduledPaymentSchema>;

export const PaymentRequestSchema = z.object({
  id: z.number(),
  requester_email: z.string(),
  target_email: z.string(),
  amount: z.number(),
  purpose: z.string().nullable(),
  status: z.string(),
  created_at: z.string(),
});

export type PaymentRequest = z.infer<typeof PaymentRequestSchema>;

// P2P Transfer
export async function createP2PTransfer(payload: {
  recipient_email: string;
  amount: number;
  commentary?: string | null;
  source_account_id?: number;
  subscriber_id?: string;
  payment_request_id?: number;
}): Promise<TransferResponse> {
  return api.post<TransferResponse>("/api/v1/p2p-transfer", payload, {
    schema: TransferResponseSchema
  });
}

export const CreateScheduledTransferSchema = z.object({
  recipient_email: z.string().email(),
  amount: z.number().positive(),
  frequency: z.enum(["daily", "weekly", "monthly"]),
  start_date: z.string(),
  end_date: z.string().nullable().optional(),
  end_condition: z.enum(["never", "date", "occurrences"]),
  max_occurrences: z.number().nullable().optional(),
});

export type CreateScheduledTransferRequest = z.infer<typeof CreateScheduledTransferSchema>;

// Scheduled Transfers
export async function createScheduledTransfer(payload: CreateScheduledTransferRequest): Promise<{ scheduled_payment_id: string }> {
  return api.post<{ scheduled_payment_id: string }>("/api/v1/transfers/scheduled", payload);
}

export async function getScheduledPayments(): Promise<ScheduledPayment[]> {
  return api.get<ScheduledPayment[]>("/api/v1/transfers/scheduled", {
    schema: z.array(ScheduledPaymentSchema)
  });
}

export async function cancelScheduledPayment(id: number): Promise<{ status: string }> {
  return api.post<{ status: string }>(`/api/v1/transfers/scheduled/${id}/cancel`, {});
}

// Payment Requests
export async function postRequest(payload: {
  target_email: string;
  amount: number;
  purpose?: string | null;
}): Promise<{ request_id: string }> {
  const res = await api.post<{ request_id: string }>("/api/v1/requests/create", payload);
  return res;
}

export async function getPaymentRequests(): Promise<PaymentRequest[]> {
  return api.get<PaymentRequest[]>("/api/v1/requests", {
    schema: z.array(PaymentRequestSchema)
  });
}

export async function handlePaymentRequestAction(
  requestId: number,
  action: "counter" | "decline",
  amount?: number
): Promise<{ status: string }> {
  const body = action === "counter" ? { amount } : null;
  return api.post<{ status: string }>(`/api/v1/requests/${requestId}/${action}`, body);
}
