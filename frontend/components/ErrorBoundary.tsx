/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

function DefaultErrorFallback({ error, errorInfo, onReset }: {
  error: Error;
  errorInfo: React.ErrorInfo | null;
  onReset: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />

      {/* Error Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="relative w-full max-w-md glass-panel rounded-[2.5rem] p-8 shadow-2xl border border-white/10"
      >
        {/* Icon */}
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-500/20 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-red-400" />
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-white text-center mb-3">
          Something went wrong
        </h2>

        {/* Message */}
        <p className="text-white/60 text-center mb-8 leading-relaxed">
          We encountered an unexpected error. Don't worry, your data is safe.
          Try refreshing the page or go back to the dashboard.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <button
            onClick={onReset}
            className="flex-1 flex items-center justify-center gap-2 h-12 px-6 rounded-2xl bg-white text-black font-semibold hover:bg-white/90 transition-all active:scale-95"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>

          <button
            onClick={() => window.location.reload()}
            className="flex-1 h-12 px-6 rounded-2xl bg-white/5 border border-white/10 text-white font-semibold hover:bg-white/10 transition-all active:scale-95"
          >
            Reload Page
          </button>
        </div>

        {/* Home Button */}
        <button
          onClick={() => window.location.href = '/'}
          className="w-full h-12 rounded-2xl bg-white/5 text-white/60 hover:text-white hover:bg-white/5 transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          Back to Home
        </button>

        {/* Error Details Toggle */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 pt-6 border-t border-white/10">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full text-left text-white/40 hover:text-white/60 text-sm font-mono transition-colors"
            >
              {showDetails ? 'Hide' : 'Show'} Error Details
            </button>

            <AnimatePresence>
              {showDetails && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mt-3 overflow-hidden"
                >
                  <div className="p-3 rounded-xl bg-black/20 border border-white/5">
                    <p className="text-red-400 text-xs font-mono mb-2">
                      {error.message}
                    </p>
                    <details className="text-white/20 text-xs font-mono">
                      <summary>Stack Trace</summary>
                      <pre className="mt-2 whitespace-pre-wrap">
                        {error.stack}
                      </pre>
                      {errorInfo && (
                        <pre className="mt-2 whitespace-pre-wrap">
                          {errorInfo.componentStack}
                        </pre>
                      )}
                    </details>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default function ErrorBoundary({ children, fallback, onError }: ErrorBoundaryProps) {
  const [state, setState] = useState<ErrorBoundaryState>({
    hasError: false,
    error: null,
    errorInfo: null,
  });
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  useEffect(() => {
    if (state.error && state.errorInfo) {
      console.error('Error Boundary caught an error:', {
        message: state.error.message,
        stack: state.error.stack,
        componentStack: state.errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      });
      onError?.(state.error, state.errorInfo);
    }
  }, [state.error, state.errorInfo, onError]);

  function handleReset() {
    if (retryCountRef.current >= maxRetries) {
      window.location.href = '/';
      return;
    }
    retryCountRef.current++;
    setState({ hasError: false, error: null, errorInfo: null });
  }

  if (state.hasError) {
    const FallbackComponent = fallback || DefaultErrorFallback;
    return (
      <FallbackComponent
        error={state.error!}
        errorInfo={state.errorInfo}
        onReset={handleReset}
      />
    );
  }

  return children;
}
