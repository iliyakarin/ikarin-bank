import { Transaction } from "@/lib/types";

export interface DashboardStats {
  totalIncome: number;
  totalExpenses: number;
  netFlow: number;
  transactionCount: number;
  pendingCount: number;
  clearedCount: number;
  averageTransaction: number;
}

export function calculateStats(transactions: Transaction[]): DashboardStats {
  const nonInternal = transactions.filter(t => t.category !== "Internal Transfer");

  const totalIncome = nonInternal
    .filter(t => t.transaction_type === "income")
    .reduce((sum, t) => sum + t.amount, 0);

  const totalExpenses = nonInternal
    .filter(t => (t.transaction_type === "expense" || t.transaction_type === "transfer") && t.amount < 0)
    .reduce((sum, t) => sum + Math.abs(t.amount), 0);

  return {
    totalIncome,
    totalExpenses,
    netFlow: totalIncome - totalExpenses,
    transactionCount: nonInternal.length,
    pendingCount: transactions.filter(t => t.status === "pending").length,
    clearedCount: transactions.filter(t => t.status === "cleared").length,
    averageTransaction: transactions.length > 0 ? totalExpenses / transactions.length : 0,
  };
}

export interface CategorySpending {
  category: string;
  amount: number;
  percentage: number;
}

export function calculateSpendingByCategory(
  transactions: Transaction[],
  limit?: number
): CategorySpending[] {
  const byCategory = transactions
    .filter(t =>
      (t.transaction_type === "expense" || t.transaction_type === "transfer") &&
      t.category !== "Internal Transfer" &&
      t.amount < 0
    )
    .reduce((acc, t) => {
      const category = t.transaction_type === "transfer" ? "Transfers" : t.category;
      acc[category] = (acc[category] || 0) + Math.abs(t.amount);
      return acc;
    }, {} as Record<string, number>);

  const total = Object.values(byCategory).reduce((a, b) => a + b, 0);
  const sorted = Object.entries(byCategory).sort((a, b) => b[1] - a[1]);
  const sliced = limit !== undefined ? sorted.slice(0, limit) : sorted;

  return sliced.map(([category, amount]) => ({
    category,
    amount,
    percentage: total > 0 ? (amount / total) * 100 : 0,
  }));
}
