"use client";

import React, { useState } from "react";
import { Clock, X } from "lucide-react";

export default function SessionExpiryWarning({
    minutes,
    onRenew,
    onDismiss,
}: {
    minutes: number;
    onRenew: () => Promise<void>;
    onDismiss: () => void;
}) {
    const [renewing, setRenewing] = useState(false);

    const handleRenew = async () => {
        setRenewing(true);
        try {
            await onRenew();
        } finally {
            setRenewing(false);
        }
    };

    const unit = minutes === 1 ? "minute" : "minutes";

    return (
        <div
            role="status"
            aria-live="polite"
            className="fixed top-4 left-1/2 -translate-x-1/2 z-[99999] flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border-2 bg-amber-950 border-amber-500 text-amber-100"
        >
            <Clock className="w-5 h-5 shrink-0" />
            <span className="font-medium text-sm">
                Your session expires in {minutes} {unit}.
            </span>
            <button
                onClick={handleRenew}
                disabled={renewing}
                className="px-3 py-1.5 rounded-lg bg-amber-500 text-amber-950 text-sm font-semibold hover:bg-amber-400 disabled:opacity-60 transition-colors"
            >
                {renewing ? "Renewing..." : "Stay signed in"}
            </button>
            <button
                onClick={onDismiss}
                aria-label="Dismiss session warning"
                className="p-1 rounded-lg hover:bg-amber-900 transition-colors"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}
