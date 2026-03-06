"use client";
import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Activity,
    Search,
    Filter,
    ChevronDown,
    ChevronUp,
    ArrowUpDown,
    Calendar,
    Shield,
    Send,
    Wallet,
    Clock,
    CreditCard,
    Settings,
    X,
    RefreshCw,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";

interface ActivityEvent {
    event_id: string;
    user_id: number;
    category: string;
    action: string;
    event_time: string;
    title: string;
    details: string;
}

const CATEGORIES = [
    { value: "", label: "All Categories", icon: Activity },
    { value: "p2p", label: "P2P & Transfers", icon: Send },
    { value: "sub_account", label: "Sub-Accounts", icon: Wallet },
    { value: "scheduled", label: "Scheduled & Recurring", icon: Clock },
    { value: "security", label: "Security & Auth", icon: Shield },
    { value: "settings", label: "Account Settings", icon: Settings },
    { value: "cards", label: "Cards & Limits", icon: CreditCard },
];

const getCategoryStyle = (category: string) => {
    switch (category) {
        case "p2p":
            return { bg: "bg-indigo-500/20", text: "text-indigo-300", border: "border-indigo-500/30" };
        case "sub_account":
            return { bg: "bg-purple-500/20", text: "text-purple-300", border: "border-purple-500/30" };
        case "scheduled":
            return { bg: "bg-amber-500/20", text: "text-amber-300", border: "border-amber-500/30" };
        case "security":
            return { bg: "bg-red-500/20", text: "text-red-300", border: "border-red-500/30" };
        case "settings":
            return { bg: "bg-teal-500/20", text: "text-teal-300", border: "border-teal-500/30" };
        case "cards":
            return { bg: "bg-cyan-500/20", text: "text-cyan-300", border: "border-cyan-500/30" };
        default:
            return { bg: "bg-white/10", text: "text-white/70", border: "border-white/20" };
    }
};

const getCategoryIcon = (category: string) => {
    const found = CATEGORIES.find((c) => c.value === category);
    return found ? found.icon : Activity;
};

const isFinancialEvent = (category: string) =>
    ["p2p", "sub_account", "scheduled"].includes(category);

export default function ActivityPage() {
    const { token, settings } = useAuth();
    const [events, setEvents] = useState<ActivityEvent[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    // Filters
    const [category, setCategory] = useState("");
    const [search, setSearch] = useState("");
    const [fromDate, setFromDate] = useState("");
    const [toDate, setToDate] = useState("");
    const [order, setOrder] = useState<"desc" | "asc">("desc");
    const [offset, setOffset] = useState(0);
    const [isCatDropdownOpen, setIsCatDropdownOpen] = useState(false);
    const limit = 30;

    const fetchActivity = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (category) params.set("category", category);
            if (search) params.set("search", search);
            if (fromDate) params.set("from_date", fromDate);
            if (toDate) params.set("to_date", toDate);
            params.set("order", order);
            params.set("limit", String(limit));
            params.set("offset", String(offset));

            const res = await fetch(
                `http://localhost:8000/api/v1/activity?${params.toString()}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (res.ok) {
                const data = await res.json();
                setEvents(data.events || []);
                setTotal(data.total || 0);
            }
        } catch (err) {
            console.error("Failed to fetch activity", err);
        } finally {
            setLoading(false);
        }
    }, [token, category, search, fromDate, toDate, order, offset]);

    useEffect(() => {
        fetchActivity();
    }, [fetchActivity]);

    // Reset offset when filters change
    useEffect(() => {
        setOffset(0);
    }, [category, search, fromDate, toDate, order]);

    const formatTime = (ts: string) => {
        const d = new Date(ts + (ts.includes("Z") ? "" : "Z"));
        return d.toLocaleString(settings.useEUDates ? "en-GB" : "en-US", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: !settings.use24Hour,
        });
    };

    const parseDetails = (raw: string): Record<string, unknown> => {
        try {
            return JSON.parse(raw);
        } catch {
            return {};
        }
    };

    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(offset / limit) + 1;

    const selectedCat = CATEGORIES.find((c) => c.value === category) || CATEGORIES[0];

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                        <Activity className="text-white" size={22} />
                    </div>
                    Activity Log
                </h1>
                <p className="text-white/50 mt-2">
                    Complete audit trail of all account events
                </p>
            </div>

            {/* Filter Bar */}
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-5">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
                    {/* Category Dropdown */}
                    <div className="md:col-span-3 relative">
                        <label className="block text-white/60 text-xs font-medium mb-1.5">
                            Category
                        </label>
                        <div
                            onClick={() => setIsCatDropdownOpen(!isCatDropdownOpen)}
                            className={`w-full bg-[#3b2d59] border ${isCatDropdownOpen ? "border-indigo-400" : "border-white/20"} rounded-xl px-4 py-2.5 text-white cursor-pointer hover:bg-[#4a3a70] transition-colors flex items-center justify-between`}
                        >
                            <span className="flex items-center gap-2 truncate">
                                {React.createElement(selectedCat.icon, { size: 16 })}
                                {selectedCat.label}
                            </span>
                            <ChevronDown
                                size={16}
                                className={`text-white/50 transition-transform ${isCatDropdownOpen ? "rotate-180" : ""}`}
                            />
                        </div>
                        <AnimatePresence>
                            {isCatDropdownOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: -8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    transition={{ duration: 0.12 }}
                                    className="absolute z-50 w-full mt-1.5 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                                >
                                    <div className="p-1.5">
                                        {CATEGORIES.map((cat) => (
                                            <div
                                                key={cat.value}
                                                onClick={() => {
                                                    setCategory(cat.value);
                                                    setIsCatDropdownOpen(false);
                                                }}
                                                className={`px-3 py-2.5 rounded-lg cursor-pointer transition-colors flex items-center gap-2 ${category === cat.value ? "bg-indigo-500/20 text-indigo-300 font-semibold" : "hover:bg-white/10 text-white"}`}
                                            >
                                                {React.createElement(cat.icon, { size: 16 })}
                                                {cat.label}
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* Search */}
                    <div className="md:col-span-3">
                        <label className="block text-white/60 text-xs font-medium mb-1.5">
                            Search
                        </label>
                        <div className="relative">
                            <Search
                                size={16}
                                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
                            />
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search events..."
                                className="w-full bg-[#3b2d59] border border-white/20 rounded-xl pl-9 pr-4 py-2.5 text-white text-sm placeholder:text-white/40 focus:outline-none focus:border-indigo-400"
                            />
                        </div>
                    </div>

                    {/* Date Range */}
                    <div className="md:col-span-2">
                        <label className="block text-white/60 text-xs font-medium mb-1.5">
                            From
                        </label>
                        <input
                            type="date"
                            value={fromDate}
                            onChange={(e) => setFromDate(e.target.value)}
                            className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-400"
                        />
                    </div>
                    <div className="md:col-span-2">
                        <label className="block text-white/60 text-xs font-medium mb-1.5">
                            To
                        </label>
                        <input
                            type="date"
                            value={toDate}
                            onChange={(e) => setToDate(e.target.value)}
                            className="w-full bg-[#3b2d59] border border-white/20 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-400"
                        />
                    </div>

                    {/* Sort + Refresh */}
                    <div className="md:col-span-2 flex gap-2">
                        <button
                            onClick={() => setOrder(order === "desc" ? "asc" : "desc")}
                            className="flex-1 bg-[#3b2d59] border border-white/20 rounded-xl px-3 py-2.5 text-white text-sm hover:bg-[#4a3a70] transition-colors flex items-center justify-center gap-1.5"
                            title={order === "desc" ? "Newest first" : "Oldest first"}
                        >
                            <ArrowUpDown size={14} />
                            {order === "desc" ? "New→Old" : "Old→New"}
                        </button>
                        <button
                            onClick={() => fetchActivity()}
                            className="bg-indigo-500/20 border border-indigo-500/30 rounded-xl px-3 py-2.5 text-indigo-300 hover:bg-indigo-500/30 transition-colors"
                            title="Refresh"
                        >
                            <RefreshCw size={16} />
                        </button>
                    </div>
                </div>

                {/* Active filters summary */}
                {(category || search || fromDate || toDate) && (
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                        <span className="text-white/40 text-xs">Active filters:</span>
                        {category && (
                            <span className="bg-indigo-500/20 text-indigo-300 text-xs px-2 py-1 rounded-lg flex items-center gap-1">
                                {selectedCat.label}
                                <X size={12} className="cursor-pointer hover:text-white" onClick={() => setCategory("")} />
                            </span>
                        )}
                        {search && (
                            <span className="bg-purple-500/20 text-purple-300 text-xs px-2 py-1 rounded-lg flex items-center gap-1">
                                &quot;{search}&quot;
                                <X size={12} className="cursor-pointer hover:text-white" onClick={() => setSearch("")} />
                            </span>
                        )}
                        {fromDate && (
                            <span className="bg-teal-500/20 text-teal-300 text-xs px-2 py-1 rounded-lg flex items-center gap-1">
                                From: {fromDate}
                                <X size={12} className="cursor-pointer hover:text-white" onClick={() => setFromDate("")} />
                            </span>
                        )}
                        {toDate && (
                            <span className="bg-teal-500/20 text-teal-300 text-xs px-2 py-1 rounded-lg flex items-center gap-1">
                                To: {toDate}
                                <X size={12} className="cursor-pointer hover:text-white" onClick={() => setToDate("")} />
                            </span>
                        )}
                        <button
                            onClick={() => { setCategory(""); setSearch(""); setFromDate(""); setToDate(""); }}
                            className="text-white/40 text-xs hover:text-white underline ml-1"
                        >
                            Clear all
                        </button>
                    </div>
                )}
            </div>

            {/* Results Count */}
            <div className="flex items-center justify-between">
                <p className="text-white/50 text-sm">
                    {total > 0
                        ? `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total} events`
                        : ""}
                </p>
                <div className="flex items-center gap-1 text-xs text-white/40">
                    <span
                        className={`inline-block w-2 h-2 rounded-full ${isFinancialEvent("p2p") ? "bg-indigo-400" : ""}`}
                    />
                    Financial
                    <span className="mx-2">|</span>
                    <span className="inline-block w-2 h-2 rounded-full bg-red-400" />
                    Administrative
                </div>
            </div>

            {/* Event List */}
            <div className="space-y-3">
                {loading ? (
                    <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-12 text-center">
                        <RefreshCw className="animate-spin text-indigo-400 mx-auto mb-3" size={28} />
                        <p className="text-white/50 font-medium">Loading activity...</p>
                    </div>
                ) : events.length === 0 ? (
                    <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-16 text-center">
                        <Activity className="text-white/20 mx-auto mb-4" size={48} />
                        <h3 className="text-white/60 text-lg font-semibold mb-2">
                            No Activity Found
                        </h3>
                        <p className="text-white/40 text-sm max-w-sm mx-auto">
                            {category || search
                                ? "Try adjusting your filters to see more events."
                                : "Your activity log is empty. Events will appear here as you use the platform."}
                        </p>
                    </div>
                ) : (
                    events.map((ev) => {
                        const style = getCategoryStyle(ev.category);
                        const Icon = getCategoryIcon(ev.category);
                        const isExpanded = expandedId === ev.event_id;
                        const details = parseDetails(ev.details);
                        const isFinancial = isFinancialEvent(ev.category);

                        return (
                            <motion.div
                                key={ev.event_id}
                                layout
                                className={`bg-white/[0.06] backdrop-blur-xl border ${isExpanded ? style.border : "border-white/10"} rounded-2xl overflow-hidden transition-colors hover:bg-white/[0.08] cursor-pointer`}
                                onClick={() =>
                                    setExpandedId(isExpanded ? null : ev.event_id)
                                }
                            >
                                {/* Main Row */}
                                <div className="flex items-center gap-4 px-5 py-4">
                                    {/* Icon */}
                                    <div
                                        className={`w-10 h-10 rounded-xl ${style.bg} flex items-center justify-center shrink-0`}
                                    >
                                        <Icon className={style.text} size={18} />
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-0.5">
                                            <span
                                                className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}
                                            >
                                                {isFinancial ? "Financial" : "Admin"}
                                            </span>
                                            <span
                                                className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/5 text-white/50`}
                                            >
                                                {ev.action.replace(/_/g, " ")}
                                            </span>
                                        </div>
                                        <p className="text-white font-medium text-sm truncate">
                                            {ev.title}
                                        </p>
                                    </div>

                                    {/* Timestamp */}
                                    <div className="text-right shrink-0">
                                        <p className="text-white/50 text-xs">
                                            {formatTime(ev.event_time)}
                                        </p>
                                    </div>

                                    {/* Chevron */}
                                    <div className="text-white/30">
                                        {isExpanded ? (
                                            <ChevronUp size={18} />
                                        ) : (
                                            <ChevronDown size={18} />
                                        )}
                                    </div>
                                </div>

                                {/* Expanded Detail Panel */}
                                <AnimatePresence>
                                    {isExpanded && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            transition={{ duration: 0.2 }}
                                            className="overflow-hidden"
                                        >
                                            <div
                                                className={`mx-5 mb-4 p-4 rounded-xl bg-black/20 border ${style.border}`}
                                            >
                                                <h4 className="text-white/60 text-xs font-semibold uppercase tracking-wider mb-3">
                                                    Detailed Information
                                                </h4>
                                                <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                                                    <div>
                                                        <span className="text-white/40 text-xs">Event ID</span>
                                                        <p className="text-white/80 text-xs font-mono break-all">
                                                            {ev.event_id}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <span className="text-white/40 text-xs">Category</span>
                                                        <p className={`${style.text} text-xs font-semibold`}>
                                                            {ev.category} / {ev.action}
                                                        </p>
                                                    </div>
                                                    {Object.entries(details).map(([key, value]) => (
                                                        <div key={key}>
                                                            <span className="text-white/40 text-xs capitalize">
                                                                {key.replace(/_/g, " ")}
                                                            </span>
                                                            <p className="text-white/80 text-xs font-mono break-all">
                                                                {String(value ?? "—")}
                                                            </p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        );
                    })
                )}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-center gap-3">
                    <button
                        disabled={currentPage <= 1}
                        onClick={() => setOffset(Math.max(0, offset - limit))}
                        className="px-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white text-sm disabled:opacity-30 hover:bg-white/20 transition-colors"
                    >
                        Previous
                    </button>
                    <span className="text-white/50 text-sm">
                        Page {currentPage} of {totalPages}
                    </span>
                    <button
                        disabled={currentPage >= totalPages}
                        onClick={() => setOffset(offset + limit)}
                        className="px-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white text-sm disabled:opacity-30 hover:bg-white/20 transition-colors"
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
