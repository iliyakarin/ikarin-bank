"use client";
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Database, MessageSquare, Settings, Eye, EyeOff, Shield, Key, Server } from 'lucide-react';

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

interface DatabaseConfigProps {
  config: DatabaseConfig;
  onChange: (config: DatabaseConfig) => void;
  onTestConnection: (source: 'clickhouse' | 'postgres' | 'kafka') => void;
  connectionStatus: Record<string, 'connected' | 'error' | 'testing' | 'idle'>;
  readOnly?: boolean;
  environment?: string;
}

export default function DatabaseConfig({ config, onChange, onTestConnection, connectionStatus, readOnly = false, environment = 'development' }: DatabaseConfigProps) {
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});

  const togglePassword = (field: string) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const updateConfig = (source: keyof DatabaseConfig, field: string, value: string) => {
    if (readOnly) return;
    onChange({
      ...config,
      [source]: {
        ...config[source],
        [field]: value
      }
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-400';
      case 'error': return 'text-red-400';
      case 'testing': return 'text-yellow-400 animate-pulse';
      default: return 'text-white/40';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return '✓';
      case 'error': return '✗';
      case 'testing': return '⟳';
      default: return '?';
    }
  };

  const isProd = environment === 'production';
  const inputClasses = `px-4 py-3 bg-black/20 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-white/20 ${readOnly ? 'cursor-default opacity-80' : ''}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-white" />
          <h3 className="text-white font-semibold">Database Configuration</h3>
        </div>
        {/* Environment Badge */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-black uppercase tracking-[0.15em] ${isProd
            ? 'bg-red-500/15 border-red-500/30 text-red-400'
            : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
          }`}>
          <Server className="w-3.5 h-3.5" />
          {environment}
        </div>
      </div>

      {/* ClickHouse Config */}
      <div className="p-6 bg-black/20 rounded-2xl border border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-white font-medium flex items-center gap-2">
            <Database className="w-4 h-4 text-orange-400" />
            ClickHouse
          </h4>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onTestConnection('clickhouse')}
              className="px-3 py-1 bg-white/10 text-white text-xs rounded-lg hover:bg-white/20 transition-all"
            >
              Test Connection
            </button>
            <span className={`text-sm font-medium ${getStatusColor(connectionStatus.clickhouse)}`}>
              {getStatusIcon(connectionStatus.clickhouse)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Host"
            value={config.clickhouse.host}
            onChange={(e) => updateConfig('clickhouse', 'host', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <input
            type="text"
            placeholder="Port"
            value={config.clickhouse.port}
            onChange={(e) => updateConfig('clickhouse', 'port', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <input
            type="text"
            placeholder="Username"
            value={config.clickhouse.username}
            onChange={(e) => updateConfig('clickhouse', 'username', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <div className="relative">
            <input
              type={showPasswords.clickhouse ? "text" : "password"}
              placeholder="Password"
              value={config.clickhouse.password}
              onChange={(e) => updateConfig('clickhouse', 'password', e.target.value)}
              readOnly={readOnly}
              className={`w-full pr-12 ${inputClasses}`}
            />
            <button
              onClick={() => togglePassword('clickhouse')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white"
            >
              {showPasswords.clickhouse ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <input
            type="text"
            placeholder="Database"
            value={config.clickhouse.database}
            onChange={(e) => updateConfig('clickhouse', 'database', e.target.value)}
            readOnly={readOnly}
            className={`md:col-span-2 ${inputClasses}`}
          />
        </div>
      </div>

      {/* PostgreSQL Config */}
      <div className="p-6 bg-black/20 rounded-2xl border border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-white font-medium flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-400" />
            PostgreSQL
          </h4>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onTestConnection('postgres')}
              className="px-3 py-1 bg-white/10 text-white text-xs rounded-lg hover:bg-white/20 transition-all"
            >
              Test Connection
            </button>
            <span className={`text-sm font-medium ${getStatusColor(connectionStatus.postgres)}`}>
              {getStatusIcon(connectionStatus.postgres)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Host"
            value={config.postgres.host}
            onChange={(e) => updateConfig('postgres', 'host', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <input
            type="text"
            placeholder="Port"
            value={config.postgres.port}
            onChange={(e) => updateConfig('postgres', 'port', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <input
            type="text"
            placeholder="Username"
            value={config.postgres.username}
            onChange={(e) => updateConfig('postgres', 'username', e.target.value)}
            readOnly={readOnly}
            className={inputClasses}
          />
          <div className="relative">
            <input
              type={showPasswords.postgres ? "text" : "password"}
              placeholder="Password"
              value={config.postgres.password}
              onChange={(e) => updateConfig('postgres', 'password', e.target.value)}
              readOnly={readOnly}
              className={`w-full pr-12 ${inputClasses}`}
            />
            <button
              onClick={() => togglePassword('postgres')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white"
            >
              {showPasswords.postgres ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <input
            type="text"
            placeholder="Database"
            value={config.postgres.database}
            onChange={(e) => updateConfig('postgres', 'database', e.target.value)}
            readOnly={readOnly}
            className={`md:col-span-2 ${inputClasses}`}
          />
        </div>
      </div>

      {/* Kafka Config */}
      <div className="p-6 bg-black/20 rounded-2xl border border-white/10 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-white font-medium flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-purple-400" />
            Kafka
          </h4>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onTestConnection('kafka')}
              className="px-3 py-1 bg-white/10 text-white text-xs rounded-lg hover:bg-white/20 transition-all"
            >
              Test Connection
            </button>
            <span className={`text-sm font-medium ${getStatusColor(connectionStatus.kafka)}`}>
              {getStatusIcon(connectionStatus.kafka)}
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            placeholder="Bootstrap Servers"
            value={config.kafka.bootstrap_servers}
            onChange={(e) => updateConfig('kafka', 'bootstrap_servers', e.target.value)}
            readOnly={readOnly}
            className={`w-full ${inputClasses}`}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              type="text"
              placeholder="Username"
              value={config.kafka.username}
              onChange={(e) => updateConfig('kafka', 'username', e.target.value)}
              readOnly={readOnly}
              className={inputClasses}
            />
            <div className="relative">
              <input
                type={showPasswords.kafka ? "text" : "password"}
                placeholder="Password"
                value={config.kafka.password}
                onChange={(e) => updateConfig('kafka', 'password', e.target.value)}
                readOnly={readOnly}
                className={`w-full pr-12 ${inputClasses}`}
              />
              <button
                onClick={() => togglePassword('kafka')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white"
              >
                {showPasswords.kafka ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
        <Shield className="w-5 h-5 text-yellow-400 flex-shrink-0" />
        <div className="text-sm text-yellow-200">
          <p className="font-medium mb-1">Security Note</p>
          <p className="text-yellow-300">
            {readOnly
              ? 'Values are sourced from server environment variables and are read-only.'
              : 'These credentials are only stored in browser memory and used for read-only operations.'}
          </p>
        </div>
      </div>
    </div>
  );
}
