'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Send,
    CreditCard,
    Wallet,
    LogOut,
    History,
    Users,
    Activity,
    Shield
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';

const navItems = [
    { name: 'Dashboard', href: '/client', icon: LayoutDashboard },
    { name: 'Payments', href: '/client/send', icon: Send },
    { name: 'My Contacts', href: '/client/contacts', icon: Users },
    { name: 'My Cards', href: '/client/cards', icon: CreditCard },
    { name: 'Activity', href: '/client/activity', icon: Activity },
    { name: 'Transactions', href: '/client/transactions', icon: History },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    const isAdmin = user?.role === 'admin';

    const items = [...navItems];
    if (isAdmin) {
        items.push({ name: 'Administration', href: '/admin', icon: Shield });
    }

    return (
        <aside className="w-20 md:w-64 h-screen bg-gradient-to-b from-white/10 via-white/5 to-transparent backdrop-blur-md border-r border-white/10 flex flex-col items-center md:items-stretch py-8 sticky top-0 transition-all duration-300 ease-in-out z-50">
            {/* Logo */}
            <div className="px-6 mb-12 flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                    <Wallet className="text-white w-6 h-6" />
                </div>
                <span className="font-bold text-xl hidden md:block tracking-tight text-white">KarinBank</span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 space-y-2 overflow-y-auto no-scrollbar">
                {items.map((item) => {
                    const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                    const Icon = item.icon;
                    return (
                        <Link key={item.name} href={item.href}>
                            <div className={`relative flex items-center gap-4 px-4 py-3 rounded-xl transition-all group ${isActive ? 'text-white font-semibold' : 'text-white/60 hover:text-white hover:bg-white/10'
                                }`}>
                                {isActive && (
                                    <motion.div
                                        layoutId="activeNav"
                                        className="absolute inset-0 bg-gradient-to-r from-purple-500/30 to-indigo-500/30 rounded-xl border border-white/20"
                                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                                    />
                                )}
                                <Icon className={`relative z-10 w-6 h-6 ${isActive ? 'text-white' : 'group-hover:text-white'
                                    }`} />
                                <span className="relative z-10 hidden md:block">{item.name}</span>
                            </div>
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom Actions */}
            <div className="px-4 mt-auto space-y-2">
                <button
                    onClick={logout}
                    className="w-full flex items-center gap-4 px-4 py-3 text-red-400/70 hover:text-red-400 hover:bg-red-500/20 rounded-xl transition-all group"
                >
                    <LogOut className="w-6 h-6" />
                    <span className="hidden md:block">Sign Out</span>
                </button>
            </div>
        </aside>
    );
}
