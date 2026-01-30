"use client";
import React, { useState } from 'react';
import { Send, Plus, CreditCard, History, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const actions = [
    { name: 'Send Money', icon: Send, color: 'bg-blue-600 hover:bg-blue-700' },
    { name: 'Request', icon: Plus, color: 'bg-black hover:bg-gray-800' },
    { name: 'New Card', icon: CreditCard, color: 'bg-purple-600 hover:bg-purple-700' },
    { name: 'History', icon: History, color: 'bg-gray-100 hover:bg-gray-200 text-black' },
];

export default function ActionHub() {
    const [activeModal, setActiveModal] = useState<string | null>(null);

    return (
        <div className="space-y-6">
            <h3 className="font-bold text-gray-900 px-1">Quick Actions</h3>
            <div className="flex flex-wrap gap-4">
                {actions.map((action) => (
                    <motion.button
                        key={action.name}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setActiveModal(action.name)}
                        className={`${action.color} text-white px-6 py-4 rounded-[1.25rem] flex items-center gap-3 font-semibold shadow-sm transition-all`}
                    >
                        <action.icon className="w-5 h-5" />
                        {action.name}
                    </motion.button>
                ))}
            </div>

            {/* Empty State Modal */}
            <AnimatePresence>
                {activeModal && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setActiveModal(null)}
                            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.9, opacity: 0, y: 20 }}
                            className="relative bg-white w-full max-w-md rounded-[2.5rem] p-8 shadow-2xl"
                        >
                            <button
                                onClick={() => setActiveModal(null)}
                                className="absolute top-6 right-6 p-2 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <X className="w-6 h-6 text-gray-400" />
                            </button>

                            <div className="space-y-6 text-center py-8">
                                <div className="w-20 h-20 bg-gray-50 rounded-[1.8rem] flex items-center justify-center mx-auto">
                                    <Plus className="w-10 h-10 text-gray-300" />
                                </div>
                                <div className="space-y-2">
                                    <h4 className="text-2xl font-bold text-gray-900">{activeModal}</h4>
                                    <p className="text-gray-500">This feature is not yet implemented.</p>
                                </div>
                                <button
                                    onClick={() => setActiveModal(null)}
                                    className="w-full bg-black text-white py-4 rounded-2xl font-bold mt-4"
                                >
                                    Dismiss
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
