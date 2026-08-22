'use client';

import React from 'react';
import { useTransactions } from '@/hooks/useDashboard';
import AnalyticsStudio from '@/components/neobank/AnalyticsStudio';

export default function AnalyticsPage() {
  const { transactions, loading } = useTransactions(720, true); // 30 days history

  return (
    <div className="pb-12">
      <AnalyticsStudio transactions={transactions} loading={loading} />
    </div>
  );
}
