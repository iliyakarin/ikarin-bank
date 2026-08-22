import React from 'react';

interface BadgeProps {
    children: React.ReactNode;
    variant?: 'primary' | 'success' | 'warning' | 'error' | 'neutral';
    icon?: React.ReactNode;
    className?: string;
}

export default function Badge({
    children,
    variant = 'neutral',
    icon,
    className = ''
}: BadgeProps) {
    const variants = {
        primary: "bg-blue-50 text-blue-600 border-blue-100",
        secondary: "bg-black text-white border-black",
        success: "bg-emerald-50 text-emerald-600 border-emerald-100",
        warning: "bg-amber-50 text-amber-600 border-amber-100",
        error: "bg-red-50 text-red-600 border-red-100",
        neutral: "bg-gray-50 text-gray-500 border-gray-100",
    };

    return (
        <span className={`
            inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold uppercase tracking-wider
            ${variants[variant]}
            ${className}
        `}>
            {icon && <span className="w-3 h-3">{icon}</span>}
            {children}
        </span>
    );
}
