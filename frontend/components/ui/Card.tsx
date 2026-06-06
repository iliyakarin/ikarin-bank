"use client";
import React from 'react';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    noPadding?: boolean;
}

const Card = React.memo(function Card({ children, className = '', noPadding = false }: CardProps) {
    return (
        <div className={`
            bg-white rounded-[2rem] border border-gray-100 shadow-sm overflow-hidden
            ${noPadding ? '' : 'p-6 md:p-8'}
            ${className}
        `}>
            {children}
        </div>
    );
}, (prev, next) => prev.className === next.className && prev.noPadding === next.noPadding && prev.children === next.children);
export default Card;
