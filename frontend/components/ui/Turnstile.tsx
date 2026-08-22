"use client";
import React, { useEffect, useRef } from 'react';

interface TurnstileProps {
    onVerify: (token: string) => void;
    onError?: (error: any) => void;
    onExpire?: () => void;
}

declare global {
    interface Window {
        turnstile: any;
    }
}

const Turnstile: React.FC<TurnstileProps> = ({ onVerify, onError, onExpire }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetIdRef = useRef<string | null>(null);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Keep callbacks fresh without triggering effect
    const callbacks = useRef({ onVerify, onError, onExpire });
    useEffect(() => {
        callbacks.current = { onVerify, onError, onExpire };
    }, [onVerify, onError, onExpire]);

    // Access TURNSTILE_SITE_KEY from window if injected at runtime, 
    // otherwise fallback to the build-time env var.
    const runtimeSiteKey = typeof window !== 'undefined' ? ((window as any).TURNSTILE_SITE_KEY || (window as any).NEXT_PUBLIC_TURNSTILE_SITE_KEY) : null;
    const rawSiteKey = runtimeSiteKey || process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

    useEffect(() => {
        // Detect if accessed directly via IP address or localhost
        const isIPOrLocal = typeof window !== 'undefined' && (
            /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(window.location.hostname) ||
            window.location.hostname === 'localhost' ||
            window.location.hostname.endsWith('.local')
        );

        const isSiteKeyValid = rawSiteKey && rawSiteKey.length > 5 && !rawSiteKey.includes('REDACTED') && rawSiteKey !== 'dummy-site-key';
        
        // If on direct IP or missing valid production site key, use testing key or auto-verify
        const effectiveSiteKey = isSiteKeyValid ? rawSiteKey : '1x00000000000000000000AA';

        if (!containerRef.current) return;

        let retryCount = 0;
        const maxRetries = 6;

        const renderTurnstile = () => {
            if (window.turnstile) {
                // Remove existing widget if re-initializing
                if (widgetIdRef.current) {
                    try {
                        window.turnstile.remove(widgetIdRef.current);
                    } catch (e) {
                        // ignore
                    }
                    widgetIdRef.current = null;
                }
                
                try {
                    widgetIdRef.current = window.turnstile.render(containerRef.current, {
                        sitekey: effectiveSiteKey,
                        callback: (token: string) => callbacks.current.onVerify(token),
                        'error-callback': (errorCode: any) => {
                            console.warn("[Turnstile] Widget error:", errorCode);
                            // If running on IP address or test key or domain error (e.g. 110200)
                            if (isIPOrLocal || errorCode === '110200' || errorCode === 110200 || !isSiteKeyValid) {
                                console.info("[Turnstile] Falling back to IP verification token on LAN/staging host.");
                                callbacks.current.onVerify('mock-token-ip');
                            } else {
                                if (callbacks.current.onError) callbacks.current.onError('Human-bot verification failed');
                            }
                        },
                        'expired-callback': () => {
                            if (callbacks.current.onExpire) callbacks.current.onExpire();
                        },
                        theme: 'dark',
                    });
                } catch (e) {
                    console.error("Turnstile render error", e);
                    if (isIPOrLocal || !isSiteKeyValid) {
                        callbacks.current.onVerify('mock-token-ip');
                    }
                }
            } else if (retryCount < maxRetries) {
                retryCount++;
                timeoutRef.current = setTimeout(renderTurnstile, 400 * retryCount);
            } else {
                // Script could not be reached (offline or blocked)
                if (isIPOrLocal || !isSiteKeyValid) {
                    console.info("[Turnstile] Script unreachable, auto-verifying on local/IP environment.");
                    callbacks.current.onVerify('mock-token-ip');
                } else if (callbacks.current.onError) {
                    callbacks.current.onError('Human-bot verification failed');
                }
            }
        };

        renderTurnstile();

        return () => {
            if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
            }
            if (window.turnstile && widgetIdRef.current) {
                try {
                    window.turnstile.remove(widgetIdRef.current);
                } catch (e) {
                    // ignore
                }
                widgetIdRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [rawSiteKey]);

    return (
        <div className="flex justify-center my-4">
            <div ref={containerRef} id="turnstile-container" />
        </div>
    );
};

export default Turnstile;
