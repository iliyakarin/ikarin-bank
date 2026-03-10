"use client";

import React from 'react';
import ErrorBoundary from '@/components/ErrorBoundary';

interface RouteErrorBoundaryProps {
  children: React.ReactNode;
  routeName: string;
}

// Route-level error boundaries for major application sections
export function ClientRouteBoundary({ children }: Omit<RouteErrorBoundaryProps, 'routeName'>) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('Client Route Error:', error);
        // You could add client-specific error tracking here
      }}
      fallback={({ error, onReset }) => (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="w-full max-w-md glass-panel rounded-[2.5rem] p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-purple-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Client Area Error</h2>
            <p className="text-white/60 mb-6">We encountered an error in the client area. Your account and data remain secure.</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onReset}
                className="flex-1 px-6 py-3 bg-white text-black rounded-xl font-medium hover:bg-white/90 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.href = '/client'}
                className="flex-1 px-6 py-3 bg-white/10 text-white rounded-xl font-medium hover:bg-white/20 transition-colors"
              >
                Dashboard
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

export function AdminRouteBoundary({ children }: Omit<RouteErrorBoundaryProps, 'routeName'>) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('Admin Route Error:', error);
        // Admin-specific error tracking with higher severity
      }}
      fallback={({ error, onReset }) => (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="w-full max-w-md glass-panel rounded-[2.5rem] p-8 text-center border border-amber-500/20">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Admin Panel Error</h2>
            <p className="text-white/60 mb-6">An error occurred in the admin panel. System operations continue normally.</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onReset}
                className="flex-1 px-6 py-3 bg-white text-black rounded-xl font-medium hover:bg-white/90 transition-colors"
              >
                Retry Admin Panel
              </button>
              <button
                onClick={() => window.location.href = '/client'}
                className="flex-1 px-6 py-3 bg-white/10 text-white rounded-xl font-medium hover:bg-white/20 transition-colors"
              >
                Leave Admin
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

export function AuthRouteBoundary({ children }: Omit<RouteErrorBoundaryProps, 'routeName'>) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('Auth Route Error:', error);
        // Authentication errors might need special handling
      }}
      fallback={({ error, onReset }) => (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="w-full max-w-md glass-panel rounded-[2.5rem] p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Authentication Error</h2>
            <p className="text-white/60 mb-6">There was an error with authentication. Please try logging in again.</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onReset}
                className="flex-1 px-6 py-3 bg-white text-black rounded-xl font-medium hover:bg-white/90 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={() => {
                  localStorage.removeItem('bank_token');
                  window.location.href = '/auth/login';
                }}
                className="flex-1 px-6 py-3 bg-white/10 text-white rounded-xl font-medium hover:bg-white/20 transition-colors"
              >
                Re-login
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
