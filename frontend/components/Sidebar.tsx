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
  BarChart3,
  Shield,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';

const navItems = [
  { name: 'Dashboard', href: '/client', icon: LayoutDashboard },
  { name: 'Smart Transfers', href: '/client/send', icon: Send },
  { name: 'Analytics Studio', href: '/client/analytics', icon: BarChart3 },
  { name: 'My Cards', href: '/client/cards', icon: CreditCard },
  { name: 'Transactions', href: '/client/transactions', icon: History },
  { name: 'My Contacts', href: '/client/contacts', icon: Users },
  { name: 'Deposit Funds', href: '/client/deposit', icon: Wallet },
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
      <div className="px-6 mb-10 flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-purple-500/20">
          <Wallet className="text-white w-5 h-5" />
        </div>
        <div>
          <span className="font-black text-xl hidden md:block tracking-tight text-white leading-none">
            KarinBank
          </span>
          <span className="text-[10px] font-mono text-purple-300 hidden md:block uppercase tracking-widest mt-0.5">
            US Neobank
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1.5 overflow-y-auto no-scrollbar">
        {items.map((item) => {
          const isActive = item.href === '/client' 
            ? pathname === '/client' 
            : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link key={item.name} href={item.href}>
              <div
                className={`relative flex items-center gap-3.5 px-4 py-3 rounded-2xl transition-all group ${
                  isActive ? 'text-white font-bold' : 'text-white/60 hover:text-white hover:bg-white/[0.06]'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute inset-0 bg-gradient-to-r from-purple-500/30 to-indigo-500/30 rounded-2xl border border-white/20 shadow-lg"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
                <Icon
                  className={`relative z-10 w-5 h-5 ${
                    isActive ? 'text-purple-300' : 'group-hover:text-white'
                  }`}
                />
                <span className="relative z-10 hidden md:block text-xs font-bold tracking-wide">
                  {item.name}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* User info & Sign Out */}
      <div className="px-4 mt-auto space-y-3">
        {user && (
          <div className="hidden md:flex items-center gap-3 p-3 rounded-2xl bg-white/[0.04] border border-white/10">
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-xs">
              {(user.first_name || user.email || 'U').slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-bold text-white block truncate">
                {user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.email}
              </span>
              <span className="text-[10px] text-white/40 font-mono block capitalize">
                {user.role} tier
              </span>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="w-full flex items-center gap-3.5 px-4 py-3 text-red-400/80 hover:text-red-400 hover:bg-red-500/10 rounded-2xl transition-all group"
        >
          <LogOut className="w-5 h-5" />
          <span className="hidden md:block text-xs font-bold">Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
