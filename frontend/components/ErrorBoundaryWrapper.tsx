"use client";

import React from 'react';
import ErrorBoundary from './ErrorBoundary';

interface ComponentErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }>;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  componentName?: string;
}

// Specialized error boundary for forms
export function FormErrorBoundary({ 
  children, 
  componentName = 'Form' 
}: ComponentErrorBoundaryProps) {
  const handleFormError = (error: Error, errorInfo: React.ErrorInfo) => {
    // Log form-specific errors
    console.error(`Form Error in ${componentName}:`, error);
    
    // You could also track form abandonment, validation errors, etc.
  };

  return (
    <ErrorBoundary
      onError={handleFormError}
      fallback={({ error, errorInfo, onReset }: { error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }) => (
        <div className="w-full p-6 glass-panel rounded-2xl border border-red-500/20">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Form Error</h3>
            <p className="text-white/60 mb-4">There was an error with this form. Your data hasn't been saved.</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={onReset}
                className="px-4 py-2 bg-white text-black rounded-xl font-medium hover:bg-white/90 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-white/10 text-white rounded-xl font-medium hover:bg-white/20 transition-colors"
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Specialized error boundary for data fetching components
export function DataErrorBoundary({ 
  children, 
  componentName = 'DataComponent' 
}: ComponentErrorBoundaryProps) {
  const handleDataError = (error: Error, errorInfo: React.ErrorInfo) => {
    // Log data-specific errors
    console.error(`Data Error in ${componentName}:`, error);
  };

  return (
    <ErrorBoundary
      onError={handleDataError}
      fallback={({ error, errorInfo, onReset }: { error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }) => (
        <div className="w-full p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Unable to Load Data</h3>
          <p className="text-white/60 mb-6">We couldn't load the latest information. Please try again.</p>
          <button
            onClick={onReset}
            className="px-6 py-3 bg-white text-black rounded-xl font-medium hover:bg-white/90 transition-colors"
          >
            Refresh Data
          </button>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Specialized error boundary for navigation
export function NavigationErrorBoundary({ 
  children 
}: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={({ error, errorInfo, onReset }: { error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }) => (
        <div className="hidden lg:flex fixed left-6 top-6 bottom-6 w-20 flex-col items-center py-10 glass-panel rounded-[2.5rem] z-50 justify-center">
          <div className="text-center">
            <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.314 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <button
              onClick={onReset}
              className="text-white/60 hover:text-white text-xs"
              title="Reset Navigation"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Specialized error boundary for charts/visualizations
export function ChartErrorBoundary({ 
  children 
}: ComponentErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={({ error, errorInfo, onReset }: { error: Error; errorInfo: React.ErrorInfo | null; onReset: () => void }) => (
        <div className="w-full h-64 glass-panel rounded-2xl flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-blue-500/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <p className="text-white/60 text-sm mb-3">Chart unavailable</p>
            <button
              onClick={onReset}
              className="text-blue-400 hover:text-blue-300 text-sm font-medium"
            >
              Try Again
            </button>
          </div>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

// Generic wrapper for easy usage
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ComponentErrorBoundaryProps, 'children'>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}