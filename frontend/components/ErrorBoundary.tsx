/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React from 'react';
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

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryCount = 0;
  private maxRetries = 3;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Log error for monitoring
    this.logError(error, errorInfo);

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  private logError = (error: Error, errorInfo: React.ErrorInfo) => {
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'SSR',
      url: typeof window !== 'undefined' ? window.location.href : 'SSR',
      retryCount: this.retryCount,
      userId: this.getUserId()
    };

    // Console logging for development
    console.error('Error Boundary caught an error:', errorData);

    // Production logging (ready for Sentry, LogRocket, etc.)
    if (process.env.NODE_ENV === 'production') {
      // This is where you'd integrate with your error monitoring service
      // Example: Sentry.captureException(error, { extra: errorData });
      this.sendToMonitoringService(errorData);
    }
  };

  private getUserId = (): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      const token = localStorage.getItem('bank_token');
      // You could decode JWT to get user ID, or store it separately
      return token ? 'authenticated-user' : 'anonymous';
    } catch {
      return null;
    }
  };

  private sendToMonitoringService = (errorData: any) => {
    // Placeholder for production monitoring service
    // In production, this would send to Sentry, LogRocket, Datadog, etc.
    try {
      // Example API call to your error logging endpoint
      fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorData),
      }).catch(() => {
        // Silently fail if error logging fails
      });
    } catch {
      // Silently fail if error logging fails
    }
  };

  private handleReset = () => {
    if (this.retryCount >= this.maxRetries) {
      // Redirect to home if max retries exceeded
      window.location.href = '/';
      return;
    }

    this.retryCount++;
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      return (
        <FallbackComponent
          error={this.state.error!}
          errorInfo={this.state.errorInfo}
          onReset={this.handleReset}
        />
      );
    }

    return this.props.children;
  }
}

// Glassmorphic Error Modal Component
interface DefaultErrorFallbackProps {
  error: Error;
  errorInfo: React.ErrorInfo | null;
  onReset: () => void;
}

function DefaultErrorFallback({ error, errorInfo, onReset }: DefaultErrorFallbackProps) {
  const [showDetails, setShowDetails] = React.useState(false);

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
