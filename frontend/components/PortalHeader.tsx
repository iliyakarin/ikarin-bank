import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { Bell, LogOut, Clock, UserCircle, Shield, Star } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useBalance } from "@/hooks/useDashboard";

export default function PortalHeader() {
  const { user, token, logout, settings } = useAuth();
  const { balance, loading: balanceLoading } = useBalance(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (token) {
      fetch("/api/v1/users/me/notifications", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data)) setNotifications(data);
        })
        .catch((err) => console.error("Failed to fetch notifications", err));
    }
  }, [token]);

  if (!user) return null;

  return (
    <header className="flex items-center justify-between mb-8 py-4 border-b border-white/10">
      <div className="flex items-center gap-4">
        <h2 className="text-white font-bold text-2xl">
          Welcome,{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
            {user.first_name} {user.last_name}
          </span>
        </h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Live Clock */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full">
          <Clock className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-white/80 tracking-wide">
            {currentTime.toLocaleString(settings.useEUDates ? "en-GB" : "en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
              hour12: !settings.use24Hour,
            })}
          </span>
        </div>

        <div className="h-6 w-px bg-white/10 mx-1 hidden md:block" />

        <div className="relative">
          <button
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            className="p-2.5 hover:bg-white/10 rounded-xl transition-all relative group"
          >
            <Bell className="w-5 h-5 text-white/60 group-hover:text-white/80" />
            {notifications.length > 0 && (
              <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </button>

          {/* Notifications Dropdown */}
          <AnimatePresence>
            {isNotifOpen && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 mt-3 w-80 bg-[#2a1f42] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50 flex flex-col"
              >
                <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                  <h3 className="text-white font-semibold flex items-center gap-2">
                    <Bell size={16} className="text-indigo-400" /> Notifications
                  </h3>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="p-6 text-center text-white/50 text-sm">
                      No new notifications
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <Link
                        href={notif.link}
                        key={notif.id}
                        onClick={() => setIsNotifOpen(false)}
                        className="p-4 border-b border-white/5 hover:bg-white/5 transition-colors flex gap-3 block"
                      >
                        <div className="mt-1 flex-shrink-0">
                          {notif.type === "transaction" ? (
                            <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                              <Clock size={14} />
                            </div>
                          ) : (
                            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                              <UserCircle size={14} />
                            </div>
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-white/90">
                            {notif.title}
                          </p>
                          <p className="text-xs text-white/60 mt-0.5">
                            {notif.message}
                          </p>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-[10px] text-white/40">
                              {new Date(notif.created_at).toLocaleDateString(settings.useEUDates ? "en-GB" : "en-US")}
                            </span>
                            {notif.amount && (
                              <span className="text-xs font-bold text-white/80">
                                ${notif.amount.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </div>
                      </Link>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="h-8 w-px bg-white/10 mx-2" />

        <Link
          href="/client/profile"
          className="flex items-center gap-3 pl-2 group transition-all"
        >
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-white leading-none group-hover:text-purple-300 transition-colors">
              {user.first_name} {user.last_name}
            </p>
            <div className="flex items-center justify-end gap-1 mt-1">
              {user.role === "admin" ? (
                <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-tighter flex items-center gap-1">
                  <Shield className="w-3 h-3" /> ADMIN
                </span>
              ) : !balanceLoading && balance !== null && balance >= 100000 ? (
                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-tighter flex items-center gap-1">
                  <Star className="w-3 h-3 fill-amber-400" /> PREMIUM MEMBER
                </span>
              ) : (
                <span className="text-[10px] font-bold text-white/60 uppercase tracking-tighter">
                  USER
                </span>
              )}
            </div>
          </div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center cursor-pointer shadow-lg shadow-purple-500/30 border-2 border-transparent group-hover:border-purple-400/50 transition-all"
          >
            <span className="text-white font-black text-sm">
              {user.first_name[0]}
              {user.last_name[0]}
            </span>
          </motion.div>
        </Link>

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
