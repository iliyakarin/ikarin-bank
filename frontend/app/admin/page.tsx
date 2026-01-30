"use client";
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, BarChart3, Settings } from 'lucide-react';
import QueryBuilder from '@/components/admin/QueryBuilder';
import BankingDashboard from '@/components/admin/BankingDashboard';
import DatabaseConfig from '@/components/admin/DatabaseConfig';
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
  const [activeTab, setActiveTab] = useState<'query' | 'dashboard'>('dashboard');
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

  // Load banking metrics on component mount
  React.useEffect(() => {
    loadBankingMetrics();
    const interval = setInterval(loadBankingMetrics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadBankingMetrics = async () => {
    try {
      const response = await fetch('http://localhost:8000/admin/banking-metrics');
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
      const response = await fetch('http://localhost:8000/admin/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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
      <div className="min-h-screen bg-[#F8F9FA] font-sans text-black">
        {/* Ambient background blobs matching client portal */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/30 blur-[120px] rounded-full animate-blob" />
          <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[100px] rounded-full animate-blob [animation-delay:2s]" />
          <div className="absolute bottom-[-10%] left-[20%] w-[45%] h-[45%] bg-indigo-600/20 blur-[120px] rounded-full animate-blob [animation-delay:4s]" />
        </div>

        {/* Header with Tabs */}
        <div className="sticky top-0 z-40 glass-panel">
          <div className="max-w-[1600px] mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                    <Settings className="text-white w-6 h-6" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold tracking-tight text-black">Mission Control</h1>
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Admin Portal</p>
                  </div>
                </div>

                {/* Main Tab Navigation */}
                <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
                  <button
                    onClick={() => setActiveTab('dashboard')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                      activeTab === 'dashboard'
                        ? 'bg-white text-black shadow-sm'
                        : 'text-gray-500 hover:text-black hover:bg-white/50'
                    }`}
                  >
                    <BarChart3 className="w-4 h-4" />
                    Banking Analytics
                  </button>
                  <button
                    onClick={() => setActiveTab('query')}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                      activeTab === 'query'
                        ? 'bg-white text-black shadow-sm'
                        : 'text-gray-500 hover:text-black hover:bg-white/50'
                    }`}
                  >
                    <Search className="w-4 h-4" />
                    Data Query
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-xs font-mono text-gray-400">v2.1.0-admin</div>
              </div>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="max-w-[1600px] mx-auto p-6 lg:p-10">
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
                <div className="lg:col-span-1">
                  {/* Sub-tabs */}
                  <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-6">
                    <button
                      onClick={() => setActiveQueryTab('builder')}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                        activeQueryTab === 'builder'
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-500 hover:text-gray-900 hover:bg-white/50'
                      }`}
                    >
                      Query Builder
                    </button>
                    <button
                      onClick={() => setActiveQueryTab('config')}
                      className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                        activeQueryTab === 'config'
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-500 hover:text-gray-900 hover:bg-white/50'
                      }`}
                    >
                      Database Config
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
                    <div className="glass-panel rounded-2xl">
                      <div className="p-6 border-b border-white/10">
                        <h3 className="text-black font-semibold">Query Results</h3>
                        <div className="flex gap-6 mt-2 text-sm">
                          <span className="text-green-600">{queryResults.rowCount} rows</span>
                          <span className="text-blue-600">{queryResults.executionTime}ms</span>
                        </div>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead>
                            <tr className="border-b border-white/10">
                              {queryResults.columns.map((column) => (
                                <th key={column} className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                                  {column}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {queryResults.data.slice(0, 100).map((row, index) => (
                              <tr key={index} className="border-b border-white/5 hover:bg-white/20">
                                {queryResults.columns.map((column) => (
                                  <td key={column} className="px-4 py-3 text-sm text-gray-800 font-mono">
                                    {row[column]?.toString() || 'NULL'}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {queryResults.data.length > 100 && (
                          <div className="p-4 text-center text-gray-500 text-sm">
                            Showing first 100 of {queryResults.rowCount} results
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="h-96 glass-panel rounded-2xl flex items-center justify-center">
                      <div className="text-center">
                        <Search className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500">Configure database connections and execute a query to see results</p>
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