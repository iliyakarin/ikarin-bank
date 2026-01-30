"use client";
import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface ButtonProps extends HTMLMotionProps<'button'> {
    variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
}

export default function Button({
    children,
    variant = 'primary',
    size = 'md',
    loading,
    className = '',
    ...props
}: ButtonProps) {
    const baseStyles = "relative inline-flex items-center justify-center gap-2 font-bold transition-all rounded-xl disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden shadow-sm active:shadow-inner";

    const variants = {
        primary: "bg-black text-white hover:bg-gray-800",
        secondary: "bg-gray-100 text-black hover:bg-gray-200",
        outline: "bg-transparent border-2 border-gray-100 text-black hover:bg-gray-50",
        danger: "bg-red-500 text-white hover:bg-red-600",
        ghost: "bg-transparent text-gray-500 hover:text-black hover:bg-gray-50",
    };

    const sizes = {
        sm: "px-4 py-2 text-sm",
        md: "px-6 py-3 text-base",
        lg: "px-8 py-4 text-lg",
    };

    return (
        <motion.button
            whileTap={{ scale: 0.98 }}
            className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
            disabled={loading}
            {...props}
        >
            {loading ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : children}
        </motion.button>
    );
}
