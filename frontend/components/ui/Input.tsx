"use client";
import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
    leftElement?: React.ReactNode;
    rightElement?: React.ReactNode;
}

export default function Input({
    label,
    error,
    helperText,
    leftElement,
    rightElement,
    className = '',
    id: customId,
    'aria-describedby': customDescribedBy,
    ...props
}: InputProps) {
    const generatedId = React.useId();
    const id = customId || generatedId;
    const errorId = `${id}-error`;
    const helperId = `${id}-helper`;
    const describedBy = [
        error ? errorId : null,
        helperText ? helperId : null,
        customDescribedBy
    ].filter(Boolean).join(' ');

    return (
        <div className="space-y-1.5 w-full">
            {label && (
                <label
                    htmlFor={id}
                    className="text-sm font-bold text-gray-700 ml-1 cursor-pointer"
                >
                    {label}
                </label>
            )}
            <div className="relative group">
                {leftElement && (
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-black transition-colors">
                        {leftElement}
                    </div>
                )}
                <input
                    {...props}
                    id={id}
                    aria-invalid={!!error}
                    aria-describedby={describedBy || undefined}
                    className={`
                        w-full bg-gray-50 border-2 border-transparent rounded-xl px-4 py-3 
                        text-black placeholder:text-gray-400 font-medium outline-none
                        transition-all duration-200
                        focus:bg-white focus:border-gray-200 focus:ring-4 focus:ring-gray-100
                        ${leftElement ? 'pl-11' : ''}
                        ${rightElement ? 'pr-11' : ''}
                        ${error ? 'border-red-100 focus:border-red-200 focus:ring-red-50/50 bg-red-50/30' : ''}
                        ${className}
                    `}
                />
                {rightElement && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2">
                        {rightElement}
                    </div>
                )}
            </div>
            {error ? (
                <p id={errorId} className="text-xs font-bold text-red-500 ml-1 mt-1" role="alert">{error}</p>
            ) : helperText ? (
                <p id={helperId} className="text-xs font-medium text-gray-400 ml-1 mt-1">{helperText}</p>
            ) : null}
        </div>
    );
}
