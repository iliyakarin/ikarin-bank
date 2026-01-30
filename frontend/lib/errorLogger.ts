// Production-ready error logging service
// Integrates with monitoring services like Sentry, LogRocket, Datadog, etc.

interface ErrorLogData {
  message: string;
  stack?: string;
  componentStack?: string;
  timestamp: string;
  userAgent: string;
  url: string;
  userId?: string | null;
  sessionId: string;
  errorId: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  tags?: Record<string, string>;
  additionalData?: Record<string, any>;
}

interface ErrorLoggerConfig {
  endpoint?: string;
  serviceName?: string;
  environment?: string;
  version?: string;
  enableConsoleLogging?: boolean;
  enableRemoteLogging?: boolean;
  maxRetries?: number;
}

class ErrorLogger {
  private config: ErrorLoggerConfig;
  private sessionId: string;

  constructor(config: ErrorLoggerConfig = {}) {
    this.config = {
      endpoint: '/api/errors',
      serviceName: 'karin-bank-frontend',
      environment: process.env.NODE_ENV || 'development',
      version: process.env.npm_package_version || '1.0.0',
      enableConsoleLogging: true,
      enableRemoteLogging: process.env.NODE_ENV === 'production',
      maxRetries: 3,
      ...config
    };

    this.sessionId = this.generateSessionId();
  }

  private generateSessionId = (): string => {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  };

  private sanitizeData = (data: any): any => {
    if (!data || typeof data !== 'object') return data;

    const sensitiveFields = [
      'password', 'token', 'secret', 'key', 'authorization',
      'cookie', 'session', 'csrf', 'jwt', 'bearer'
    ];

    const sanitized = { ...data };

    const sanitizeRecursively = (obj: any, path: string = ''): any => {
      if (Array.isArray(obj)) {
        return obj.map((item, index) => sanitizeRecursively(item, `${path}[${index}]`));
      }

      if (obj && typeof obj === 'object') {
        const result: any = {};
        for (const [key, value] of Object.entries(obj)) {
          const currentPath = path ? `${path}.${key}` : key;
          const lowerKey = key.toLowerCase();

          if (sensitiveFields.some(field => lowerKey.includes(field))) {
            result[key] = '[REDACTED]';
          } else if (typeof value === 'object' && value !== null) {
            result[key] = sanitizeRecursively(value, currentPath);
          } else {
            result[key] = value;
          }
        }
        return result;
      }

      return obj;
    };

    return sanitizeRecursively(sanitized);
  };

  private generateErrorId = (): string => {
    return 'error_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  };

  private determineSeverity = (error: Error): ErrorLogData['severity'] => {
    // Check for critical error patterns
    const criticalPatterns = [
      /network.*error/i,
      /authentication.*failed/i,
      /permission.*denied/i,
      /quota.*exceeded/i,
      /security.*violation/i
    ];

    const mediumPatterns = [
      /failed.*to.*fetch/i,
      /timeout/i,
      /connection/i
    ];

    if (criticalPatterns.some(pattern => pattern.test(error.message))) {
      return 'critical';
    }

    if (mediumPatterns.some(pattern => pattern.test(error.message))) {
      return 'medium';
    }

    return 'low';
  };

  private async sendToRemote(data: ErrorLogData): Promise<void> {
    if (!this.config.enableRemoteLogging || !this.config.endpoint) {
      return;
    }

    const retries = this.config.maxRetries || 3;
    let attempt = 0;

    while (attempt < retries) {
      try {
        const response = await fetch(this.config.endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Error-ID': data.errorId,
            'X-Session-ID': data.sessionId,
          },
          body: JSON.stringify(data),
        });

        if (response.ok) {
          return;
        }

        attempt++;
        if (attempt < retries) {
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      } catch (err) {
        attempt++;
        if (attempt < retries) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      }
    }

    // If all retries failed, log to console
    if (this.config.enableConsoleLogging) {
      console.error('Failed to send error to remote service:', data);
    }
  };

  public logError = (
    error: Error,
    additionalData: ErrorLogData['additionalData'] = {},
    tags: ErrorLogData['tags'] = {}
  ): void => {
    const errorId = this.generateErrorId();
    const severity = this.determineSeverity(error);

    const logData: ErrorLogData = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'SSR',
      url: typeof window !== 'undefined' ? window.location.href : 'SSR',
      userId: this.getUserId(),
      sessionId: this.sessionId,
      errorId,
      severity,
      tags: {
        serviceName: this.config.serviceName || 'karin-bank-frontend',
        environment: this.config.environment || 'development',
        version: this.config.version || '1.0.0',
        ...tags
      } as Record<string, string>,
      additionalData: this.sanitizeData(additionalData)
    };

    // Console logging
    if (this.config.enableConsoleLogging) {
      const consoleMethod = severity === 'critical' ? 'error' : 
                           severity === 'high' ? 'error' :
                           severity === 'medium' ? 'warn' : 'info';
      
      console[consoleMethod](`[${severity.toUpperCase()}] ${errorId}:`, {
        error: error.message,
        stack: error.stack,
        ...logData.additionalData
      });
    }

    // Remote logging
    this.sendToRemote(logData).catch(() => {
      // Silently fail if remote logging fails
    });

    // Integration with monitoring services
    this.integrateWithMonitoringServices(error, logData);
  };

  private getUserId = (): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      const token = localStorage.getItem('bank_token');
      return token ? 'authenticated-user' : 'anonymous';
    } catch {
      return null;
    }
  };

  private integrateWithMonitoringServices = (error: Error, logData: ErrorLogData): void => {
    // Sentry Integration (if available)
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        tags: logData.tags,
        extra: logData.additionalData,
        user: { id: logData.userId }
      });
    }

    // LogRocket Integration (if available)
    if (typeof window !== 'undefined' && (window as any).LogRocket) {
      (window as any).LogRocket.captureException(error, {
        tags: logData.tags,
        extra: logData.additionalData
      });
    }

    // Datadog Integration (if available)
    if (typeof window !== 'undefined' && (window as any).DD_LOGS) {
      (window as any).DD_LOGS.logger.error(error.message, {
        error: logData,
        errorId: logData.errorId,
        sessionId: logData.sessionId
      });
    }
  };

  public logUserAction = (action: string, data: any = {}): void => {
    if (!this.config.enableConsoleLogging) return;

    console.info(`[USER ACTION] ${action}:`, this.sanitizeData(data));
  };

  public logPerformance = (metric: string, value: number, unit: string = 'ms'): void => {
    if (!this.config.enableConsoleLogging) return;

    console.info(`[PERFORMANCE] ${metric}: ${value}${unit}`);
  };

  // Create a global error handler for unhandled errors
  public setupGlobalHandlers = (): void => {
    if (typeof window === 'undefined') return;

    // Handle unhandled JavaScript errors
    window.addEventListener('error', (event) => {
      this.logError(event.error || new Error(event.message), {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      }, { source: 'unhandled-error' });
    });

    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.logError(
        new Error(event.reason?.message || 'Unhandled Promise Rejection'),
        { reason: event.reason },
        { source: 'unhandled-promise-rejection' }
      );
    });
  };
}

// Create singleton instance
export const errorLogger = new ErrorLogger();

// Initialize global error handlers
if (typeof window !== 'undefined') {
  errorLogger.setupGlobalHandlers();
}

export default errorLogger;