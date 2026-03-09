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
    }
  ],
  postgres: [
    {
      name: "All Users with Accounts",
      query: "SELECT u.id, u.first_name, u.last_name, u.email, a.balance FROM users u LEFT JOIN accounts a ON u.id = a.user_id ORDER BY u.created_at DESC",
      description: "All users with their current account balances"
    },
    {
      name: "Recent Transactions",
      query: "SELECT t.*, u.first_name, u.last_name FROM transactions t JOIN users u ON t.account_id = u.id ORDER BY t.created_at DESC LIMIT 50",
      description: "Latest 50 transactions with user information"
    },
    {
      name: "Account Balance Distribution",
      query: "SELECT CASE WHEN balance < 100 THEN 'Low' WHEN balance < 1000 THEN 'Medium' WHEN balance < 10000 THEN 'High' ELSE 'Very High' END as balance_range, COUNT(*) as account_count FROM accounts GROUP BY balance_range",
      description: "Distribution of account balances across ranges"
    },
    {
      name: "User Registration Trends",
      query: "SELECT DATE(created_at) as date, COUNT(*) as new_users FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' GROUP BY DATE(created_at) ORDER BY date DESC",
      description: "New user registrations over past 30 days"
    }
  ],
  kafka: [
    {
      name: "Recent Kafka Messages",
      query: "get_recent_messages",
      description: "Recent messages from bank_transactions topic (last 100)"
    },
    {
      name: "Topic Message Count",
      query: "get_topic_stats",
      description: "Message count and consumer lag for bank_transactions topic"
    },
    {
      name: "Consumer Group Status",
      query: "get_consumer_groups",
      description: "Status of all consumer groups for banking topics"
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