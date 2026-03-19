'use client';
import { motion } from 'framer-motion';
import { CreditCard, Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

export default function MyCardsPage() {
    const [showDebitCVV, setShowDebitCVV] = useState(false);
    const [showCreditCVV, setShowCreditCVV] = useState(false);

    const debitCard = {
        number: '5542 8890 1223 4567',
        name: 'JOHN DOE',
        expiry: '12/27',
        cvv: '123'
    };

    const creditCard = {
        number: '4532 1488 0343 6467',
        name: 'JOHN DOE',
        expiry: '08/26',
        cvv: '456'
    };

    return (
        <div className="space-y-8 pb-12">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-2"
            >
                <h1 className="text-4xl font-black text-white flex items-center gap-3">
                    <CreditCard className="text-purple-400" size={32} />
                    My Cards
                </h1>
                <p className="text-white/60">Manage your debit and credit cards</p>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Debit Card */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    className="h-64 rounded-3xl overflow-hidden shadow-2xl"
                >
                    <div className="h-full bg-gradient-to-br from-slate-400 via-slate-500 to-slate-700 p-6 flex flex-col justify-between relative overflow-hidden">
                        {/* Background decoration */}
                        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20"></div>

                        {/* Chip */}
                        <div className="relative z-10 w-12 h-10 bg-gradient-to-br from-yellow-300 to-yellow-600 rounded-lg shadow-lg"></div>

                        {/* Card details */}
                        <div className="relative z-10 space-y-4">
                            <p className="text-white/80 text-sm font-semibold tracking-wider">DEBIT CARD</p>
                            <p className="text-white text-2xl font-mono tracking-wider">{debitCard.number}</p>

                            <div className="flex justify-between items-end">
                                <div>
                                    <p className="text-white/60 text-xs">CARDHOLDER</p>
                                    <p className="text-white font-semibold">{debitCard.name}</p>
                                </div>
                                <div>
                                    <p className="text-white/60 text-xs">EXPIRES</p>
                                    <p className="text-white font-mono">{debitCard.expiry}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Credit Card */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    className="h-64 rounded-3xl overflow-hidden shadow-2xl"
                >
                    <div className="h-full bg-gradient-to-br from-amber-400 via-amber-500 to-amber-700 p-6 flex flex-col justify-between relative overflow-hidden">
                        {/* Background decoration */}
                        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20"></div>

                        {/* Chip */}
                        <div className="relative z-10 w-12 h-10 bg-gradient-to-br from-yellow-300 to-yellow-600 rounded-lg shadow-lg"></div>

                        {/* Card details */}
                        <div className="relative z-10 space-y-4">
                            <p className="text-white/80 text-sm font-semibold tracking-wider">CREDIT CARD • PREMIUM</p>
                            <p className="text-white text-2xl font-mono tracking-wider">{creditCard.number}</p>

                            <div className="flex justify-between items-end">
                                <div>
                                    <p className="text-white/60 text-xs">CARDHOLDER</p>
                                    <p className="text-white font-semibold">{creditCard.name}</p>
                                </div>
                                <div>
                                    <p className="text-white/60 text-xs">EXPIRES</p>
                                    <p className="text-white font-mono">{creditCard.expiry}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Card Details Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="grid grid-cols-1 lg:grid-cols-2 gap-8"
            >
                {/* Debit Card Details */}
                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8">
                    <h3 className="text-xl font-bold text-white mb-6">Debit Card Details</h3>
                    <div className="space-y-4">
                        <div>
                            <p className="text-white/60 text-sm">Card Number</p>
                            <p className="text-white font-mono">{debitCard.number}</p>
                        </div>
                        <div>
                            <p className="text-white/60 text-sm">Expiration Date</p>
                            <p className="text-white font-semibold">{debitCard.expiry}</p>
                        </div>
                        <div>
                            <p className="text-white/60 text-sm">CVV</p>
                            <div className="flex items-center gap-2">
                                <p className="text-white font-mono">{showDebitCVV ? debitCard.cvv : '•••'}</p>
                                <button
                                    onClick={() => setShowDebitCVV(!showDebitCVV)}
                                    className="text-white/60 hover:text-white transition-colors"
                                >
                                    {showDebitCVV ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Credit Card Details */}
                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8">
                    <h3 className="text-xl font-bold text-white mb-6">Credit Card Details</h3>
                    <div className="space-y-4">
                        <div>
                            <p className="text-white/60 text-sm">Card Number</p>
                            <p className="text-white font-mono">{creditCard.number}</p>
                        </div>
                        <div>
                            <p className="text-white/60 text-sm">Expiration Date</p>
                            <p className="text-white font-semibold">{creditCard.expiry}</p>
                        </div>
                        <div>
                            <p className="text-white/60 text-sm">CVV</p>
                            <div className="flex items-center gap-2">
                                <p className="text-white font-mono">{showCreditCVV ? creditCard.cvv : '•••'}</p>
                                <button
                                    onClick={() => setShowCreditCVV(!showCreditCVV)}
                                    className="text-white/60 hover:text-white transition-colors"
                                >
                                    {showCreditCVV ? <EyeOff size={16} /> : <Eye size={16} />}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Info Box */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-purple-500/10 border border-purple-500/30 rounded-2xl p-6"
            >
                <p className="text-purple-200 text-sm">
                    ✨ These are mock cards for demonstration purposes. Never share your actual card details with anyone.
                </p>
            </motion.div>
        </div>
    );
}
