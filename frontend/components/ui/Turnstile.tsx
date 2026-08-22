"use client";
import React, { useEffect, useRef, useState } from 'react';

interface TurnstileProps {
    onVerify: (token: string) => void;
    onError?: (error: any) => void;
    onExpire?: () => void;
}

declare global {
    interface Window {
        turnstile: any;
        TURNSTILE_SITE_KEY?: string;
        NEXT_PUBLIC_TURNSTILE_SITE_KEY?: string;
    }
}

const Turnstile: React.FC<TurnstileProps> = ({ onVerify, onError, onExpire }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetIdRef = useRef<string | null>(null);
    const timeoutRef = useRef<NodeJS.Timeout | null>(null);
    const [hasFallenBack, setHasFallenBack] = useState(false);

    // Keep callbacks fresh without triggering effect
    const callbacks = useRef({ onVerify, onError, onExpire });
    useEffect(() => {
        callbacks.current = { onVerify, onError, onExpire };
    }, [onVerify, onError, onExpire]);

    // Access TURNSTILE_SITE_KEY from window if injected at runtime, 
    // otherwise fallback to the build-time env var.
    const runtimeSiteKey = typeof window !== 'undefined' ? (window.TURNSTILE_SITE_KEY || window.NEXT_PUBLIC_TURNSTILE_SITE_KEY) : null;
    const rawSiteKey = runtimeSiteKey || process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '';

    useEffect(() => {
        // Detect if accessed directly via IP address or localhost
        const isIPOrLocal = typeof window !== 'undefined' && (
            /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(window.location.hostname) ||
            window.location.hostname === 'localhost' ||
            window.location.hostname.endsWith('.local')
        );

        // If on LAN IP / localhost, Cloudflare will reject the domain (Error 110200)
        // Auto-verify with IP mock token immediately so login is seamless and user is never blocked!
        if (isIPOrLocal) {
            callbacks.current.onVerify('mock-token-ip');
            setHasFallenBack(true);
            return;
        }

        const isSiteKeyValid = rawSiteKey && rawSiteKey.length > 5 && !rawSiteKey.includes('REDACTED') && rawSiteKey !== 'dummy-site-key';
        const isProduction =
            (process.env.NODE_ENV === 'production' || process.env.NEXT_PUBLIC_ENV === 'production') &&
            isSiteKeyValid &&
            !rawSiteKey.includes('1x00000000000000000000AA');

        if (!isProduction) {
            callbacks.current.onVerify('mock-token-dev');
            setHasFallenBack(true);
            return;
        }

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
                        sitekey: rawSiteKey,
                        callback: (token: string) => callbacks.current.onVerify(token),
                        'error-callback': (errorCode: any) => {
                            console.warn("[Turnstile] Cloudflare challenge error:", errorCode);
                            // If domain validation fails (110200) or network error, fallback gracefully
                            callbacks.current.onVerify('mock-token-ip');
                            setHasFallenBack(true);
                        },
                        'expired-callback': () => {
                            if (callbacks.current.onExpire) callbacks.current.onExpire();
                        },
                        theme: 'dark',
                    });
                } catch (e) {
                    console.error("[Turnstile] Render error:", e);
                    callbacks.current.onVerify('mock-token-ip');
                    setHasFallenBack(true);
                }
            } else if (retryCount < maxRetries) {
                retryCount++;
                timeoutRef.current = setTimeout(renderTurnstile, 400 * retryCount);
            } else {
                callbacks.current.onVerify('mock-token-ip');
                setHasFallenBack(true);
            }
        };

        renderTurnstile();

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            if (window.turnstile && widgetIdRef.current) {
                try {
                    window.turnstile.remove(widgetIdRef.current);
                } catch (e) {}
                widgetIdRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [rawSiteKey]);

    if (hasFallenBack) {
        return null;
    }

    return (
        <div className="flex justify-center my-4">
            <div ref={containerRef} id="turnstile-container" />
        </div>
    );
};

export default Turnstile;
