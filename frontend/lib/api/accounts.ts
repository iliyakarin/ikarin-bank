import { z } from "zod";
import { api } from "./client";

/**
 * Accounts API Service
 */

export const AccountSchema = z.object({
  id: z.number(),
  user_id: z.number().optional(),
  account_number: z.string().optional(),
  routing_number: z.string().nullable().optional(),
  balance: z.number(),
  reserved_balance: z.number().optional().default(0),
  currency: z.string().optional().default("USD"),
  is_main: z.boolean(),
  name: z.string(),
  masked_account_number: z.string().nullable().optional(),
});

export type Account = z.infer<typeof AccountSchema>;

export const TransactionSchema = z.object({
  id: z.string(),
  account_id: z.number(),
  merchant: z.string(),
  amount: z.number(),
  category: z.string(),
  status: z.enum(['pending', 'sent_to_kafka', 'cleared']),
  description: z.string().optional(),
  transaction_type: z.enum(['income', 'expense', 'transfer']),
  transaction_side: z.enum(['DEBIT', 'CREDIT']).optional(),
  created_at: z.string(),
});

export type Transaction = z.infer<typeof TransactionSchema>;

export const AccountSummarySchema = z.object({
  balance: z.number(),
  reserved_balance: z.number(),
  accounts: z.array(AccountSchema),
});

export type AccountSummary = z.infer<typeof AccountSummarySchema>;

export async function getAccounts(): Promise<Account[]> {
  const res = await api.get<AccountSummary>("/api/v1/accounts", {
    schema: AccountSummarySchema
  });
  return res.accounts;
}

export async function getAccountSummary(userId: number): Promise<AccountSummary> {
  return api.get<AccountSummary>(`/api/v1/accounts/${userId}`, {
    schema: AccountSummarySchema
  });
}

export async function getRecentTransactions(hours: number = 24): Promise<Transaction[]> {
  const res = await api.get<{ transactions: Transaction[] }>(`/api/v1/recent-transactions`, {
    params: { hours: hours.toString() },
    schema: z.object({ transactions: z.array(TransactionSchema) })
  });
  return res.transactions;
}

export async function getAccountTransactions(accountId: number): Promise<Transaction[]> {
  return api.get<Transaction[]>(`/api/v1/accounts/${accountId}/transactions`, {
    schema: z.array(TransactionSchema)
  });
}
