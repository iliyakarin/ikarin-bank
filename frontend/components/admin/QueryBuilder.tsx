"use client";
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, BarChart3, Database, MessageSquare, Filter, Calendar, User, Clock } from 'lucide-react';
import { DataErrorBoundary } from '@/components/ErrorBoundaryWrapper';

interface QueryBuilderProps {
  onQuery: (query: string, params: any) => void;
  loading: boolean;
  dbConfig: any;
}

const PREDEFINED_QUERIES = {
  clickhouse: [
    {
      name: "All Transactions (24h)",
      query: "SELECT * FROM bank_transactions WHERE created_at >= now() - INTERVAL 1 DAY ORDER BY created_at DESC",
      description: "Shows all banking transactions from the past 24 hours"
    },
    {
      name: "High Value Transactions",
      query: "SELECT * FROM bank_transactions WHERE amount > 1000 ORDER BY amount DESC LIMIT 100",
      description: "Transactions with amounts over $1,000"
    },
    {
      name: "User Transaction History",
      query: "SELECT * FROM bank_transactions WHERE account_id = {user_id} ORDER BY created_at DESC LIMIT 50",
      description: "All transactions for specific user (requires user_id parameter)",
      params: ['user_id']
    },
    {
      name: "Hourly Transaction Volume",
      query: "SELECT toHour(created_at) as hour, COUNT(*) as count, SUM(amount) as total FROM bank_transactions WHERE created_at >= now() - INTERVAL 1 DAY GROUP BY hour ORDER BY hour",
      description: "Transaction volume grouped by hour"
    },
    {
      name: "Top Merchants by Volume",
      query: "SELECT merchant, COUNT(*) as transaction_count, SUM(amount) as total_amount FROM bank_transactions WHERE created_at >= now() - INTERVAL 7 DAY GROUP BY merchant ORDER BY total_amount DESC LIMIT 20",
      description: "Top 20 merchants by transaction volume (7 days)"
    },
    {
      name: "Daily Volume Trends",
      query: "SELECT toDate(created_at) as date, SUM(amount) as volume FROM bank_transactions GROUP BY date ORDER BY date DESC LIMIT 30",
      description: "Daily transaction volume for the last 30 days"
    },
    {
      name: "Category Distribution",
      query: "SELECT category, COUNT(*) as count, SUM(amount) as total FROM bank_transactions GROUP BY category ORDER BY total DESC",
      description: "Spending patterns by transaction category"
    },
    {
      name: "Average Transaction Size",
      query: "SELECT AVG(amount) FROM bank_transactions",
      description: "Global average transaction amount"
    },
    {
      name: "Peak Usage Hours",
      query: "SELECT toHour(created_at) as hr, count(*) as c FROM bank_transactions GROUP BY hr ORDER BY c DESC",
      description: "Hours with highest transaction density"
    },
    {
      name: "System Errors & Returns",
      query: "SELECT * FROM bank_transactions WHERE status = 'failed' OR amount < 0 LIMIT 50",
      description: "Trace failed or reversed transactions"
    }
  ],
  postgres: [
    {
      name: "All Users Registry",
      query: "SELECT id, first_name, last_name, email, role, created_at FROM users ORDER BY created_at DESC",
      description: "Complete member directory from PostgreSQL"
    },
    {
      name: "Account Balances",
      query: "SELECT u.email, a.balance, a.name FROM users u JOIN accounts a ON u.id = a.user_id",
      description: "Current ledger balances for all users"
    },
    {
      name: "Transaction Audit Log",
      query: "SELECT * FROM transactions ORDER BY created_at DESC LIMIT 100",
      description: "Raw transaction log from the main relational database"
    },
    {
      name: "Idempotency Records",
      query: "SELECT * FROM idempotency_keys ORDER BY created_at DESC LIMIT 50",
      description: "Verify API execution consistency records"
    },
    {
      name: "Scheduled Payments",
      query: "SELECT * FROM scheduled_payments WHERE status = 'Active'",
      description: "All currently active recurring transfers"
    },
    {
      name: "Pending Requests",
      query: "SELECT * FROM payment_requests WHERE status = 'pending_target'",
      description: "Unclaimed peer-to-peer payment requests"
    },
    {
      name: "Outbox Queue Status",
      query: "SELECT status, COUNT(*) FROM outbox GROUP BY status",
      description: "Current status of the Kafka event relay queue"
    },
    {
      name: "Admin Audit Trail",
      query: "SELECT * FROM users WHERE role = 'admin'",
      description: "Identify all users with administrative privileges"
    },
    {
      name: "System Totals (Assets)",
      query: "SELECT SUM(balance) as total_assets FROM accounts",
      description: "Cumulative balance of all accounts in the system"
    },
    {
      name: "Recent Signups",
      query: "SELECT email, created_at FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'",
      description: "New users registered in the last week"
    }
  ],
  kafka: [
    {
      name: "Recent Stream Events",
      query: "get_recent_messages",
      description: "Listen to the bank_transactions live message stream"
    },
    {
      name: "Topic Telemetry",
      query: "get_topic_stats",
      description: "Real-time stats for the banking topic"
    },
    {
      name: "Consumer Health",
      query: "get_consumer_groups",
      description: "Check status of event consumers and lag"
    },
    {
      name: "Outbox Heartbeat",
      query: "get_outbox_telemetry",
      description: "Live monitoring of the Outbox Worker relay"
    },
    {
      name: "Event Latency",
      query: "get_stream_latency",
      description: "Message propagation delay (ms)"
    },
    {
      name: "Stream Errors",
      query: "get_error_stream",
      description: "High-level Kafka technical error logs"
    },
    {
      name: "Partition Mapping",
      query: "get_partition_data",
      description: "Analyze message distribution across partitions"
    },
    {
      name: "Producer Status",
      query: "get_producer_health",
      description: "Verify the API backend's connection to the cluster"
    },
    {
      name: "Message Geometry",
      query: "get_message_sizes",
      description: "Payload size distribution telemetry"
    },
    {
      name: "System Snapshots",
      query: "get_topic_snapshots",
      description: "Historical high-water marks for the 24h cycle"
    }
  ]
};

export default function QueryBuilder({ onQuery, loading, dbConfig }: QueryBuilderProps) {
  const [selectedSource, setSelectedSource] = useState<'clickhouse' | 'postgres' | 'kafka'>('clickhouse');
  const [selectedQuery, setSelectedQuery] = useState(PREDEFINED_QUERIES.clickhouse[0]);
  const [customQuery, setCustomQuery] = useState('');
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});

  const handleExecuteQuery = () => {
    const query = isCustomMode ? customQuery : selectedQuery.query;
    const params = isCustomMode ? {} : queryParams;

    if (query.trim()) {
      onQuery(query, {
        source: selectedSource,
        ...params,
        dbConfig
      });
    }
  };

  const handleQuerySelect = (query: any) => {
    setSelectedQuery(query);
    setIsCustomMode(false);
    setQueryParams({});
  };

  const renderQueryParamInput = (paramName: string) => (
    <input
      key={paramName}
      type="text"
      placeholder={`Enter ${paramName}`}
      value={queryParams[paramName] || ''}
      onChange={(e) => setQueryParams(prev => ({ ...prev, [paramName]: e.target.value }))}
      className="px-3 py-2 bg-black/20 border border-white/10 rounded-lg text-white placeholder-white/40 text-sm focus:outline-none focus:border-white/20"
    />
  );

  return (
    <div className="space-y-6">
      {/* Source Selection */}
      <div className="flex gap-2 p-1 bg-black/20 rounded-xl">
        {(['clickhouse', 'postgres', 'kafka'] as const).map((source) => (
          <button
            key={source}
            onClick={() => {
              setSelectedSource(source);
              setSelectedQuery(PREDEFINED_QUERIES[source][0]);
              setIsCustomMode(false);
            }}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${selectedSource === source
              ? 'bg-white/10 text-white shadow-sm border border-white/10'
              : 'text-white/60 hover:text-white hover:bg-white/5'
              }`}
          >
            {source === 'clickhouse' && <Database className="w-4 h-4" />}
            {source === 'postgres' && <Database className="w-4 h-4" />}
            {source === 'kafka' && <MessageSquare className="w-4 h-4" />}
            <span className="text-sm capitalize">{source}</span>
          </button>
        ))}
      </div>

      {/* Query Selection */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold flex items-center gap-2">
            <Search className="w-4 h-4" />
            Query Builder
          </h3>
          <button
            onClick={() => setIsCustomMode(!isCustomMode)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${isCustomMode
              ? 'bg-purple-500 text-white'
              : 'bg-white/10 text-white/60 hover:text-white'
              }`}
          >
            {isCustomMode ? 'Predefined' : 'Custom SQL'}
          </button>
        </div>

        {!isCustomMode ? (
          <div className="space-y-3">
            <select
              value={selectedQuery?.name || ''}
              onChange={(e) => {
                const query = PREDEFINED_QUERIES[selectedSource].find(q => q.name === e.target.value);
                if (query) handleQuerySelect(query);
              }}
              className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white focus:outline-none focus:border-white/20"
            >
              {PREDEFINED_QUERIES[selectedSource].map((query) => (
                <option key={query.name} value={query.name} className="bg-black">
                  {query.name}
                </option>
              ))}
            </select>

            {selectedQuery && (
              <div className="p-4 bg-black/20 rounded-xl border border-white/10">
                <p className="text-white/60 text-sm mb-3">{selectedQuery.description}</p>
                <pre className="text-green-400 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                  {selectedQuery.query}
                </pre>

                {/* Parameter Inputs */}
                {selectedQuery.params && selectedQuery.params.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-white/40 text-xs font-medium">Parameters:</p>
                    <div className="flex gap-2 flex-wrap">
                      {selectedQuery.params.map(renderQueryParamInput)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <textarea
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Enter custom query..."
              className="w-full h-32 px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white placeholder-white/40 font-mono text-sm focus:outline-none focus:border-white/20 resize-none"
            />
            <p className="text-white/40 text-xs">
              Enter custom SQL for ClickHouse/PostgreSQL or use Kafka API methods
            </p>
          </div>
        )}

        {/* Execute Button */}
        <button
          onClick={handleExecuteQuery}
          disabled={loading || (!isCustomMode && selectedQuery?.params?.some(p => !queryParams[p]))}
          className="w-full py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-semibold rounded-xl hover:from-purple-600 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Executing Query...
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Execute Query
            </>
          )}
        </button>
      </div>
    </div>
  );
}