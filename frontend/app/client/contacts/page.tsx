'use client';
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trash2, Plus, Users, Search, UserCircle, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/AuthContext';

type Contact = {
    id: number;
    contact_name: string;
    contact_email: string;
    created_at: string;
};

export default function ContactsPage() {
    const { token } = useAuth();
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);

    // Add Contact form state
    const [newName, setNewName] = useState('');
    const [newEmail, setNewEmail] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        if (token) {
            fetchContacts();
        }
    }, [token]);

    const fetchContacts = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/v1/contacts', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setContacts(data);
            }
        } catch (err) {
            console.error('Failed to fetch contacts', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAddContact = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setActionLoading(true);

        try {
            const res = await fetch('http://localhost:8000/api/v1/contacts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    contact_name: newName,
                    contact_email: newEmail
                })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Failed to add contact');
            }

            setSuccess('Contact added successfully!');
            setNewName('');
            setNewEmail('');
            fetchContacts();

            setTimeout(() => setSuccess(''), 3000);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setActionLoading(false);
        }
    };

    const handleDeleteContact = async (id: number) => {
        if (!confirm('Are you sure you want to delete this contact?')) return;

        try {
            const res = await fetch(`http://localhost:8000/api/v1/contacts/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (res.ok) {
                setContacts(contacts.filter(c => c.id !== id));
            } else {
                const data = await res.json();
                alert(data.detail || 'Failed to delete contact');
            }
        } catch (err) {
            console.error('Failed to delete contact', err);
            alert('An error occurred');
        }
    };

    const filteredContacts = contacts.filter(c =>
        c.contact_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.contact_email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="max-w-6xl mx-auto space-y-8">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">My Contacts</h1>
                    <p className="text-white/60">Manage your saved contacts for fast and easy payments.</p>
                </div>

                <div className="relative w-full md:w-72">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                    <input
                        type="text"
                        placeholder="Search contacts..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
                    />
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Add Contact Form */}
                <div className="lg:col-span-1">
                    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 sticky top-8">
                        <div className="w-12 h-12 bg-gradient-to-br from-purple-500/20 to-indigo-500/20 rounded-xl flex items-center justify-center mb-6">
                            <Plus className="w-6 h-6 text-purple-400" />
                        </div>
                        <h2 className="text-xl font-bold text-white mb-6">Add New Contact</h2>

                        <form onSubmit={handleAddContact} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-white/70 mb-2">Contact Name</label>
                                <input
                                    type="text"
                                    required
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                    placeholder="e.g. Alice Smith"
                                    className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-white/70 mb-2">Email Address</label>
                                <input
                                    type="email"
                                    required
                                    value={newEmail}
                                    onChange={(e) => setNewEmail(e.target.value)}
                                    placeholder="alice@example.com"
                                    className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                />
                            </div>

                            {error && <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400 text-sm">{error}</div>}
                            {success && <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-xl text-green-400 text-sm">{success}</div>}

                            <button
                                type="submit"
                                disabled={actionLoading || !newName.trim() || !newEmail.trim()}
                                className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium py-3 rounded-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {actionLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Save Contact'}
                            </button>
                        </form>
                    </div>
                </div>

                {/* Contact List */}
                <div className="lg:col-span-2 space-y-4">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl">
                            <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-4" />
                            <p className="text-white/60">Loading contacts...</p>
                        </div>
                    ) : filteredContacts.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl text-center px-4">
                            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
                                <Users className="w-8 h-8 text-white/40" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">No contacts found</h3>
                            <p className="text-white/60 max-w-sm">
                                {searchQuery ? 'Try adjusting your search query.' : 'Add your first contact using the form to easily send and request payments.'}
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <AnimatePresence>
                                {filteredContacts.map((contact) => (
                                    <motion.div
                                        key={contact.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        className="bg-white/5 backdrop-blur-xl border border-white/10 p-5 rounded-2xl flex items-center justify-between group hover:bg-white/10 transition-colors"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-full flex items-center justify-center">
                                                <UserCircle className="w-6 h-6 text-indigo-400" />
                                            </div>
                                            <div>
                                                <h3 className="text-white font-semibold text-lg">{contact.contact_name}</h3>
                                                <p className="text-white/50 text-sm truncate max-w-[150px] sm:max-w-[200px]">{contact.contact_email}</p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => handleDeleteContact(contact.id)}
                                            className="p-3 text-white/30 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                                            title="Delete contact"
                                        >
                                            <Trash2 className="w-5 h-5" />
                                        </button>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
