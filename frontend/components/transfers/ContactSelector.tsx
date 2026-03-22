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
  const filteredContacts = contacts.filter(c => 
    c.email.toLowerCase().includes(value.toLowerCase()) || 
    (c.name && c.name.toLowerCase().includes(value.toLowerCase()))
  );

  return (
    <div className="space-y-3 relative">
      <label className="block text-white font-semibold">{label}</label>
      <div className="relative">
        <input
          type="email"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder={placeholder}
          className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder:text-white/40 focus:outline-none focus:border-purple-400 pr-10 transition-all"
          required
        />
        <ChevronDown 
          className={`absolute right-4 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
          size={20} 
        />
      </div>

      <AnimatePresence>
        {isOpen && filteredContacts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute z-[120] w-full mt-2 bg-[#2a1f42] border border-white/10 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto backdrop-blur-xl"
          >
            <div className="p-2 space-y-1">
              {filteredContacts.map(c => (
                <div
                  key={c.id}
                  onClick={() => {
                    onChange(c.email);
                    setIsOpen(false);
                  }}
                  className="px-4 py-3 hover:bg-white/10 rounded-lg cursor-pointer flex items-center gap-3 group transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 group-hover:bg-purple-500 group-hover:text-white transition-colors">
                    {c.name ? c.name.charAt(0).toUpperCase() : <User size={14} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate group-hover:text-purple-300">{c.name || c.email}</p>
                    {c.name && <p className="text-white/40 text-xs truncate flex items-center gap-1"><Mail size={10} /> {c.email}</p>}
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
