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
    const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '[REDACTED]';

    useEffect(() => {
        const isSiteKeyValid = siteKey && siteKey.length > 5 && !siteKey.includes('REDACTED');
        const isProduction =
            (process.env.NODE_ENV === 'production' || process.env.NEXT_PUBLIC_ENV === 'production') &&
            isSiteKeyValid &&
            !siteKey.includes('1x00000000000000000000AA') &&
            siteKey !== 'dummy-site-key';

        if (!isProduction) {
            onVerify('mock-token-dev');
            return;
        }


        if (!containerRef.current) return;

        let retryCount = 0;
        const maxRetries = 10;

        const renderTurnstile = () => {
            if (window.turnstile) {
                window.turnstile.render(containerRef.current, {
                    sitekey: siteKey,
                    callback: onVerify,
                    'error-callback': () => {
                        if (onError) onError('Human-bot verification failed');
                    },
                    'expired-callback': onExpire,
                    theme: 'dark',
                });
            } else if (retryCount < maxRetries) {
                // If script not loaded yet, retry with backoff
                retryCount++;
                setTimeout(renderTurnstile, 500 * retryCount);
            } else {
                if (onError) onError('Human-bot verification failed');
            }
        };


        renderTurnstile();

        return () => {
            if (window.turnstile && containerRef.current) {
                containerRef.current.innerHTML = '';
            }
        };
    }, [onVerify, onError, onExpire, siteKey]);

    return (
        <div className="flex justify-center my-4">
            <div ref={containerRef} id="turnstile-container" />
        </div>
    );
};

export default Turnstile;
