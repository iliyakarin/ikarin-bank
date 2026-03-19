"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";

interface DatePickerProps {
    value: string;
    onChange: (date: string) => void;
    label?: string;
    placeholder?: string;
    className?: string;
    required?: boolean;
}

export default function DatePicker({
    value,
    onChange,
    label,
    placeholder = "Select date",
    className = "",
    required = false,
}: DatePickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [currentDate, setCurrentDate] = useState(value ? new Date(value + 'T00:00:00') : new Date());
    const containerRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const formatDate = (date: Date) => {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    };

    const handleDateClick = (dayIdx: number, year: number, month: number) => {
        const selectedDate = new Date(year, month, dayIdx);
        onChange(formatDate(selectedDate));
        setIsOpen(false);
    };

    const handleToday = () => {
        const today = new Date();
        onChange(formatDate(today));
        setCurrentDate(today);
        setIsOpen(false);
    };

    const handleClear = () => {
        onChange("");
        setIsOpen(false);
    };

    const nextMonth = () => {
        const next = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
        setCurrentDate(next);
    };

    const prevMonth = () => {
        const prev = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
        setCurrentDate(prev);
    };

    const getDaysInMonth = (year: number, month: number) => {
        return new Date(year, month + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (year: number, month: number) => {
        return new Date(year, month, 1).getDay();
    };

    const renderHeader = () => {
        const monthNames = ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        return (
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <span className="text-white font-bold">
                        {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
                    </span>
                    <motion.div
                        whileHover={{ rotate: 90 }}
                        className="text-white/40 cursor-pointer"
                    >
                        <ChevronRight size={16} />
                    </motion.div>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        type="button"
                        onClick={prevMonth}
                        className="p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <button
                        type="button"
                        onClick={nextMonth}
                        className="p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>
        );
    };

    const renderDaysHeader = () => {
        const days = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
        return (
            <div className="grid grid-cols-7 mb-2">
                {days.map((day) => (
                    <div key={day} className="text-center text-xs font-bold text-white/40 py-2">
                        {day}
                    </div>
                ))}
            </div>
        );
    };

    const renderCells = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const daysInMonth = getDaysInMonth(year, month);
        const firstDay = getFirstDayOfMonth(year, month);

        // Fill previous month days
        const prevMonthDays = getDaysInMonth(year, month - 1);
        const cells = [];

        for (let i = firstDay - 1; i >= 0; i--) {
            const dayNum = prevMonthDays - i;
            cells.push(
                <div key={`prev-${dayNum}`} className="flex items-center justify-center h-10 w-10 text-sm text-white/20">
                    {dayNum}
                </div>
            );
        }

        // Fill current month days
        const selectedDateStr = value;
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let i = 1; i <= daysInMonth; i++) {
            const dateObj = new Date(year, month, i);
            const dateStr = formatDate(dateObj);
            const isSelected = selectedDateStr === dateStr;
            const isToday = formatDate(today) === dateStr;

            cells.push(
                <div
                    key={i}
                    className={`
                    flex items-center justify-center h-10 w-10 text-sm cursor-pointer rounded-lg transition-all
                    ${isSelected ? "bg-indigo-400 !text-slate-900 font-bold shadow-[0_4px_12px_rgba(129,140,248,0.4)]" : "text-white hover:bg-white/10"}
                    ${isToday && !isSelected ? "border border-indigo-500/50" : ""}
                `}
                    onClick={() => handleDateClick(i, year, month)}
                >
                    {i}
                </div>
            );
        }

        // Fill next month days
        const remaining = 42 - cells.length; // 6 rows
        for (let i = 1; i <= remaining; i++) {
            cells.push(
                <div key={`next-${i}`} className="flex items-center justify-center h-10 w-10 text-sm text-white/20">
                    {i}
                </div>
            );
        }

        return <div className="grid grid-cols-7 px-2 pb-2">{cells}</div>;
    };

    return (
        <div className={`space-y-3 relative ${className}`} ref={containerRef}>
            {label && <label className="block text-white font-semibold">{label}</label>}
            <div className="relative">
                <div
                    onClick={() => setIsOpen(!isOpen)}
                    className={`
            w-full bg-[#3b2d59] border ${isOpen ? 'border-indigo-400' : 'border-white/20'}
            rounded-xl px-4 py-3 text-white cursor-pointer hover:bg-[#4a3a70]
            transition-colors flex items-center justify-between shadow-inner
          `}
                >
                    <span className={!value ? "text-white/40" : ""}>
                        {value || placeholder}
                    </span>
                    <CalendarIcon className="text-white/40" size={18} />
                </div>

                <AnimatePresence>
                    {isOpen && (
                        <motion.div
                            initial={{ opacity: 0, y: -10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -10, scale: 0.95 }}
                            transition={{ duration: 0.15, ease: "easeOut" }}
                            className="absolute z-[110] mt-2 bg-[#2a1f42] border border-white/10 rounded-2xl shadow-2xl overflow-hidden w-80 backdrop-blur-xl"
                        >
                            {renderHeader()}
                            <div className="p-2">
                                {renderDaysHeader()}
                                {renderCells()}
                            </div>
                            <div className="flex items-center justify-between px-4 py-3 border-t border-white/10">
                                <button
                                    type="button"
                                    onClick={handleClear}
                                    className="text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                    Clear
                                </button>
                                <button
                                    type="button"
                                    onClick={handleToday}
                                    className="text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                    Today
                                </button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
