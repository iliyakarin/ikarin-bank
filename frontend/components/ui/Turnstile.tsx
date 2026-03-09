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
    const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'; // Testing key

    useEffect(() => {
        // Auto-verify in development
        if (process.env.NEXT_PUBLIC_ENV !== 'production') {
            onVerify('mock-token-dev');
            return;
        }

        if (!containerRef.current) return;

        const renderTurnstile = () => {
            if (window.turnstile) {
                window.turnstile.render(containerRef.current, {
                    sitekey: siteKey,
                    callback: onVerify,
                    'error-callback': onError,
                    'expired-callback': onExpire,
                    theme: 'dark',
                });
            } else {
                // If script not loaded yet, retry in 500ms
                setTimeout(renderTurnstile, 500);
            }
        };

        renderTurnstile();

        return () => {
            if (window.turnstile && containerRef.current) {
                // Cleanup if needed (Turnstile might not have explicit remove but clearing innerHTML is common)
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
