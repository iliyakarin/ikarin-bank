"use client";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, User, Mail } from "lucide-react";
import { Contact } from "@/lib/api/contacts";

interface ContactSelectorProps {
  contacts: Contact[];
  value: string;
  onChange: (email: string) => void;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  label?: string;
  placeholder?: string;
}

export default function ContactSelector({
  contacts,
  value,
  onChange,
  isOpen,
  setIsOpen,
  label = "Recipient Email",
  placeholder = "user@example.com"
}: ContactSelectorProps) {
  const filteredContacts = contacts.filter(c => {
    const emailMatch = (c.email || "").toLowerCase().includes(value.toLowerCase());
    const nameMatch = (c.name || "").toLowerCase().includes(value.toLowerCase());
    return emailMatch || nameMatch;
  });

  return (
    <div className="space-y-3 relative">
      <label className="block text-white/60 font-bold text-sm uppercase tracking-wider">{label}</label>
      <div className="relative group">
        <input
          type="email"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-4 text-white placeholder:text-white/20 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 pr-10 transition-all"
          required
        />
        <ChevronDown 
          className={`absolute right-4 top-1/2 -translate-y-1/2 text-white/20 pointer-events-none transition-all duration-300 group-focus-within:text-indigo-400 ${isOpen ? 'rotate-180' : ''}`} 
          size={20} 
        />
      </div>

      <AnimatePresence>
        {isOpen && filteredContacts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="absolute z-[120] w-full mt-2 bg-slate-900/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto"
          >
            <div className="p-2 space-y-1">
              {filteredContacts.map(c => (
                <div
                  key={c.id}
                  onClick={() => {
                    onChange(c.email);
                    setIsOpen(false);
                  }}
                  className="px-4 py-3 hover:bg-white/10 rounded-xl cursor-pointer flex items-center gap-3 group/item transition-colors border border-transparent"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-indigo-400 font-black group-hover/item:bg-indigo-500 group-hover/item:text-white transition-all border border-white/10">
                    {c.name ? c.name.charAt(0).toUpperCase() : <User size={18} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-bold truncate group-hover/item:text-indigo-400">{c.name || c.email}</p>
                    {c.name && <p className="text-white/40 text-[10px] font-medium truncate flex items-center gap-1 uppercase tracking-wider"><Mail size={10} /> {c.email}</p>}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

