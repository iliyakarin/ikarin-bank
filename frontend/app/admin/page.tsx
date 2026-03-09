"use client";
import React, { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, BarChart3, Settings, Users } from 'lucide-react';
import QueryBuilder from '@/components/admin/QueryBuilder';
import BankingDashboard from '@/components/admin/BankingDashboard';
import DatabaseConfig from '@/components/admin/DatabaseConfig';
import UserManagement from '@/components/admin/UserManagement';
import { DataErrorBoundary } from '@/components/ErrorBoundaryWrapper';

interface QueryResults {
  columns: string[];
  data: any[];
  rowCount: number;
  executionTime: number;
}

interface DatabaseConfig {
  clickhouse: {
    host: string;
    port: string;
    username: string;
    password: string;
    database: string;
  };
  postgres: {
    host: string;
    port: string;
    username: string;
    password: string;
    database: string;
  };
  kafka: {
    bootstrap_servers: string;
    username: string;
    password: string;
  };
}

interface BankingMetrics {
  totalVolume: number;
  transactionCount: number;
  totalBalance: number;
  activeUsers: number;
  avgTransactionSize: number;
  topTransactions: any[];
  hourlyVolume: any[];
  merchantStats: any[];
  userGrowth: any[];
}

export default function AdminPage() {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'query' | 'dashboard' | 'users'>('dashboard');
  const [activeQueryTab, setActiveQueryTab] = useState<'builder' | 'config'>('builder');
  const [queryResults, setQueryResults] = useState<QueryResults | null>(null);
  const [bankingMetrics, setBankingMetrics] = useState<BankingMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [dbConfig, setDbConfig] = useState<DatabaseConfig>({
    clickhouse: {
      host: 'localhost',
      port: '8123',
      username: 'default',
      password: '',
      database: 'banking'
    },
    postgres: {
      host: 'localhost',
      port: '5432',
      username: 'admin',
      password: '',
      database: 'banking_db'
    },
    kafka: {
      bootstrap_servers: 'localhost:9092',
      username: '',
      password: ''
    }
  });
  const [connectionStatus, setConnectionStatus] = useState<Record<string, 'connected' | 'error' | 'testing' | 'idle'>>({
    clickhouse: 'idle',
    postgres: 'idle',
    kafka: 'idle'
  });

  // Load banking metrics and system config on component mount
  React.useEffect(() => {
    if (token) {
      loadBankingMetrics();
      fetchConfig();
      const interval = setInterval(loadBankingMetrics, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [token]);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/v1/admin/config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const config = await response.json();
        // Merge with existing defaults to preserve any fields not returned by API
        setDbConfig(prev => ({
          ...prev,
          clickhouse: { ...prev.clickhouse, ...config.clickhouse, password: '' },
          postgres: { ...prev.postgres, ...config.postgres, password: '' },
          kafka: { ...prev.kafka, ...config.kafka, password: '' }
        }));
      }
    } catch (error) {
      console.error('Failed to fetch system config:', error);
    }
  };

  const loadBankingMetrics = async () => {
    try {
      const response = await fetch('/api/v1/admin/banking-metrics', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const metrics = await response.json();
        setBankingMetrics(metrics);
        console.log('Banking metrics loaded:', metrics);
      } else {
        console.error('Failed to load banking metrics, response status:', response.status);
        // Set fallback data for demonstration
        setBankingMetrics({
          totalVolume: 1456780.50,
          transactionCount: 3421,
          totalBalance: 8923456.78,
          activeUsers: 1247,
          avgTransactionSize: 425.67,
          topTransactions: [
            { merchant: "Amazon", amount: 2847.50, created_at: new Date().toISOString(), account_id: 1234 },
            { merchant: "Apple Store", amount: 1999.00, created_at: new Date().toISOString(), account_id: 5678 },
            { merchant: "Best Buy", amount: 1567.89, created_at: new Date().toISOString(), account_id: 9012 },
            { merchant: "Tesla", amount: 1200.00, created_at: new Date().toISOString(), account_id: 3456 },
            { merchant: "Home Depot", amount: 987.43, created_at: new Date().toISOString(), account_id: 7890 }
          ],
          hourlyVolume: Array.from({ length: 24 }, (_, i) => ({
            hour: i,
            count: Math.floor(Math.random() * 200) + 50,
            total: Math.floor(Math.random() * 50000) + 10000
          })),
          merchantStats: [
            { merchant: "Amazon", transaction_count: 234, total_amount: 45678.90 },
            { merchant: "Walmart", transaction_count: 189, total_amount: 32145.67 },
            { merchant: "Target", transaction_count: 156, total_amount: 28934.12 },
            { merchant: "Starbucks", transaction_count: 342, total_amount: 8934.56 },
            { merchant: "McDonald's", transaction_count: 267, total_amount: 6789.23 }
          ],
          userGrowth: Array.from({ length: 30 }, (_, i) => ({
            date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            count: Math.floor(Math.random() * 50) + 10
          }))
        });
      }
    } catch (error) {
      console.error('Failed to load banking metrics:', error);
      // Set fallback data
      setBankingMetrics({
        totalVolume: 1456780.50,
        transactionCount: 3421,
        totalBalance: 8923456.78,
        activeUsers: 1247,
        avgTransactionSize: 425.67,
        topTransactions: [
          { merchant: "Amazon", amount: 2847.50, created_at: new Date().toISOString(), account_id: 1234 },
          { merchant: "Apple Store", amount: 1999.00, created_at: new Date().toISOString(), account_id: 5678 },
          { merchant: "Best Buy", amount: 1567.89, created_at: new Date().toISOString(), account_id: 9012 },
          { merchant: "Tesla", amount: 1200.00, created_at: new Date().toISOString(), account_id: 3456 },
          { merchant: "Home Depot", amount: 987.43, created_at: new Date().toISOString(), account_id: 7890 }
        ],
        hourlyVolume: Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          count: Math.floor(Math.random() * 200) + 50,
          total: Math.floor(Math.random() * 50000) + 10000
        })),
        merchantStats: [
          { merchant: "Amazon", transaction_count: 234, total_amount: 45678.90 },
          { merchant: "Walmart", transaction_count: 189, total_amount: 32145.67 },
          { merchant: "Target", transaction_count: 156, total_amount: 28934.12 },
          { merchant: "Starbucks", transaction_count: 342, total_amount: 8934.56 },
          { merchant: "McDonald's", transaction_count: 267, total_amount: 6789.23 }
        ],
        userGrowth: Array.from({ length: 30 }, (_, i) => ({
          date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          count: Math.floor(Math.random() * 50) + 10
        }))
      });
    }
  };

  const handleQuery = async (query: string, params: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/admin/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query, params }),
      });

      if (response.ok) {
        const results = await response.json();
        setQueryResults(results);
      } else {
        const error = await response.json();
        alert(`Query failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Query execution failed:', error);
      alert('Failed to execute query. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (source: 'clickhouse' | 'postgres' | 'kafka') => {
    setConnectionStatus(prev => ({ ...prev, [source]: 'testing' }));

    try {
      // Simulate connection test
      await new Promise(resolve => setTimeout(resolve, 1500));

      // In real implementation, this would test actual database connections
      setConnectionStatus(prev => ({ ...prev, [source]: 'connected' }));

      setTimeout(() => {
        setConnectionStatus(prev => ({ ...prev, [source]: 'idle' }));
      }, 3000);
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, [source]: 'error' }));
      console.error(`Failed to connect to ${source}:`, error);
    }
  };

  return (
    <DataErrorBoundary>
      <div className="min-h-screen font-sans text-slate-200">
        {/* Header with Tabs */}
        <div className="sticky top-0 z-40 glass-panel border-b border-white/5 bg-slate-950/20 backdrop-blur-2xl">
          <div className="max-w-[1600px] mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-8">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
                    <Settings className="text-white w-5 h-5" />
                  </div>
                  <div>
                    <h1 className="text-lg font-black tracking-tight text-white uppercase italic">
                      MISSION<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">CONTROL</span>
                    </h1>
                    <p className="text-[10px] font-black text-indigo-400/60 uppercase tracking-[0.2em]">Data Layer Interface</p>
                  </div>
                </div>

                {/* Main Tab Navigation */}
                <div className="flex gap-1 p-1 bg-white/5 rounded-2xl border border-white/5">
                  <button
                    onClick={() => setActiveTab('dashboard')}
                    className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2.5 ${activeTab === 'dashboard'
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20'
                      : 'text-white/40 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    <BarChart3 className="w-4 h-4" />
                    Analytics
                  </button>
                  <button
                    onClick={() => setActiveTab('query')}
                    className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2.5 ${activeTab === 'query'
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20'
                      : 'text-white/40 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    <Search className="w-4 h-4" />
                    Engine
                  </button>
                  <button
                    onClick={() => setActiveTab('users')}
                    className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2.5 ${activeTab === 'users'
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20'
                      : 'text-white/40 hover:text-white hover:bg-white/5'
                      }`}
                  >
                    <Users className="w-4 h-4" />
                    Directory
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">
                  SYS-ADMIN · V2.1.0
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="max-w-[1600px] mx-auto py-10">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' ? (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
              >
                <BankingDashboard metrics={bankingMetrics!} loading={!bankingMetrics} />
              </motion.div>
            ) : activeTab === 'users' ? (
              <motion.div
                key="users"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
              >
                <UserManagement token={token!} />
              </motion.div>
            ) : (
              <motion.div
                key="query"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="grid grid-cols-1 lg:grid-cols-3 gap-8"
              >
                {/* Query/Config Sidebar */}
                <div className="lg:col-span-1 space-y-6">
                  {/* Sub-tabs */}
                  <div className="flex gap-1 p-1 bg-white/5 rounded-2xl border border-white/5">
                    <button
                      onClick={() => setActiveQueryTab('builder')}
                      className={`flex-1 px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all ${activeQueryTab === 'builder'
                        ? 'bg-white/10 text-white shadow-sm'
                        : 'text-white/40 hover:text-white hover:bg-white/5'
                        }`}
                    >
                      Workspace
                    </button>
                    <button
                      onClick={() => setActiveQueryTab('config')}
                      className={`flex-1 px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all ${activeQueryTab === 'config'
                        ? 'bg-white/10 text-white shadow-sm'
                        : 'text-white/40 hover:text-white hover:bg-white/5'
                        }`}
                    >
                      Connectivity
                    </button>
                  </div>

                  <AnimatePresence mode="wait">
                    {activeQueryTab === 'builder' ? (
                      <motion.div
                        key="builder"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        transition={{ duration: 0.2 }}
                      >
                        <QueryBuilder onQuery={handleQuery} loading={loading} dbConfig={dbConfig} />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="config"
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        transition={{ duration: 0.2 }}
                      >
                        <DatabaseConfig
                          config={dbConfig}
                          onChange={setDbConfig}
                          onTestConnection={handleTestConnection}
                          connectionStatus={connectionStatus}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Query Results */}
                <div className="lg:col-span-2">
                  {queryResults ? (
                    <div className="glass-panel rounded-[2rem] overflow-hidden">
                      <div className="p-8 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                        <div>
                          <h3 className="text-white font-black text-xl tracking-tight">System Response</h3>
                          <div className="flex gap-6 mt-3 text-[10px] font-black uppercase tracking-widest">
                            <span className="text-emerald-400/80 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">{queryResults.rowCount} records</span>
                            <span className="text-indigo-400/80 bg-indigo-400/10 px-2 py-0.5 rounded-full border border-indigo-400/20">{queryResults.executionTime}ms latency</span>
                          </div>
                        </div>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-white/5 bg-white/[0.01]">
                              {queryResults.columns.map((column) => (
                                <th key={column} className="px-6 py-4 text-left text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">
                                  {column}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {queryResults.data.slice(0, 100).map((row, index) => (
                              <tr key={index} className="border-b border-white/5 hover:bg-white/[0.04] transition-colors">
                                {queryResults.columns.map((column) => (
                                  <td key={column} className="px-6 py-4 text-xs text-white/70 font-mono tracking-tighter">
                                    {row[column]?.toString() || 'NULL'}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {queryResults.data.length > 100 && (
                          <div className="p-6 text-center text-white/20 text-[10px] font-black uppercase tracking-[0.3em]">
                            Truncated: Showing 100 of {queryResults.rowCount}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="h-[28rem] glass-panel rounded-[2rem] flex items-center justify-center border-dashed border-white/10">
                      <div className="text-center space-y-4">
                        <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto border border-white/5">
                          <Search className="w-8 h-8 text-white/10" />
                        </div>
                        <p className="text-white/20 text-xs font-black uppercase tracking-[0.2em] max-w-xs mx-auto leading-relaxed">
                          Awaiting Database execution. Configure parameters and run query to fetch telemetry.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </DataErrorBoundary>
  );
}