"use client";
import React from 'react';
import { useAuth } from '@/lib/AuthContext';
import { Bell, LogOut } from 'lucide-react';
import { motion } from 'framer-motion';

export default function PortalHeader() {
    const { user, logout } = useAuth();

    if (!user) return null;

    return (
        <header className="flex items-center justify-between mb-8 py-4 border-b border-white/10">
            <div className="flex items-center gap-4">
                <h2 className="text-white font-bold text-2xl">
                    Welcome, <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">{user.first_name} {user.last_name}</span>
                </h2>
            </div>

            <div className="flex items-center gap-4">
                <button className="p-2.5 hover:bg-white/10 rounded-xl transition-all relative group">
                    <Bell className="w-5 h-5 text-white/60 group-hover:text-white/80" />
                    <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full" />
                </button>

                <div className="h-8 w-px bg-white/10 mx-2" />

                <div className="flex items-center gap-3 pl-2">
                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-bold text-white leading-none">
                            {user.first_name} {user.last_name}
                        </p>
                        <p className="text-[10px] font-bold text-white/60 uppercase tracking-tighter mt-1">
                            Premium Member
                        </p>
                    </div>
                    <motion.div
                        whileHover={{ scale: 1.05 }}
                        className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center cursor-pointer shadow-lg shadow-purple-500/30"
                    >
                        <span className="text-white font-black text-sm">
                            {user.first_name[0]}{user.last_name[0]}
                        </span>
                    </motion.div>
                </div>

                <button
                    onClick={logout}
                    className="p-2.5 hover:bg-red-500/20 rounded-xl transition-all group"
                    title="Sign Out"
                >
                    <LogOut className="w-5 h-5 text-white/60 group-hover:text-red-400" />
                </button>
            </div>
        </header>
    );
}
