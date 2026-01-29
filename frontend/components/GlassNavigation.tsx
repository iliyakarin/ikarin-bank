"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Send, CreditCard, PieChart, Settings } from "lucide-react";

const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Transfer", href: "/transfer", icon: Send },
    { name: "Cards", href: "/cards", icon: CreditCard },
    { name: "Analytics", href: "/analytics", icon: PieChart },
    { name: "Settings", href: "/settings", icon: Settings },
];

export default function GlassNavigation() {
    const pathname = usePathname();

    return (
        <>
            {/* Sidebar - Desktop */}
            <aside className="hidden lg:flex fixed left-6 top-6 bottom-6 w-20 flex-col items-center py-10 glass-panel rounded-[2.5rem] z-50">
                <div className="w-10 h-10 bg-primary-600 rounded-2xl flex items-center justify-center text-white font-black text-xl mb-12">
                    K
                </div>

                <nav className="flex flex-col gap-6">
                    {navItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = pathname === item.href;
                        return (
                            <Link key={item.href} href={item.href}>
                                <motion.div
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.9 }}
                                    className={`p-3 rounded-2xl transition-all duration-300 ${isActive ? "bg-white/10 text-white shadow-lg" : "text-white/40 hover:text-white/70"
                                        }`}
                                >
                                    <Icon size={24} />
                                </motion.div>
                            </Link>
                        );
                    })}
                </nav>

                <div className="mt-auto mb-4">
                    <div className="w-10 h-10 rounded-full border-2 border-white/20 p-0.5 overflow-hidden">
                        <div className="w-full h-full bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-full" />
                    </div>
                </div>
            </aside>

            {/* Bottom Nav - Mobile */}
            <nav className="lg:hidden fixed bottom-6 left-6 right-6 h-16 glass-panel rounded-full flex items-center justify-around px-6 z-50">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                        <Link key={item.href} href={item.href}>
                            <motion.div
                                whileTap={{ scale: 0.8 }}
                                className={`p-2 rounded-xl transition-all ${isActive ? "text-white bg-white/10" : "text-white/40"
                                    }`}
                            >
                                <Icon size={24} />
                            </motion.div>
                        </Link>
                    );
                })}
            </nav>
        </>
    );
}
