"use client";
import { useState } from 'react';

export default function TransferForm() {
    const [loading, setLoading] = useState(false);

    const handleTransfer = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        // We send data to our FastAPI backend
        await fetch('http://localhost:8000/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                account_id: 1, // Hardcoded for this fun project
                amount: 100.50,
                category: "Transfer",
                merchant: "Friend"
            }),
        });
        setLoading(false);
        alert("Transfer Initiated!");
    };

    return (
        <div className="p-6 bg-white rounded-xl shadow-md">
            <h2 className="text-xl font-bold mb-4">Payments</h2>
            <button
                onClick={handleTransfer}
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
            >
                {loading ? "Processing..." : "Quick Transfer $100.50"}
            </button>
        </div>
    );
}