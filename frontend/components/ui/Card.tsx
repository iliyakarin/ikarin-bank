"use client";
import React from 'react';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    noPadding?: boolean;
}

export default function Card({ children, className = '', noPadding = false }: CardProps) {
    return (
        <div className={`
            bg-white rounded-[2rem] border border-gray-100 shadow-sm overflow-hidden
            ${noPadding ? '' : 'p-6 md:p-8'}
            ${className}
        `}>
            {children}
        </div>
    );
}
