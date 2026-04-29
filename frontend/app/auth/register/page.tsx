"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Wallet, Key, Mail, User, ShieldCheck, RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Card from '@/components/ui/Card';
import Link from 'next/link';
import Turnstile from '@/components/ui/Turnstile';

export default function RegisterPage() {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        password: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [captchaToken, setCaptchaToken] = useState<string | null>(null);
    const [turnstileKey, setTurnstileKey] = useState(0);
    const router = useRouter();

    const generatePassword = () => {
        const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+";
        const array = new Uint32Array(16);
        window.crypto.getRandomValues(array);
        let password = "";
        for (let i = 0; i < 16; i++) {
            password += charset.charAt(array[i] % charset.length);
        }
        setFormData({ ...formData, password });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const res = await fetch('/api/v1/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...formData, captcha_token: captchaToken }),
            });

            if (res.ok) {
                router.push('/auth/login');
            } else {
                const data = await res.json();
                setError(data.detail || 'Registration failed');
                setCaptchaToken(null);
                setTurnstileKey(k => k + 1);
            }
        } catch (err) {
            setError('Connection error. Is the API running?');
            setCaptchaToken(null);
            setTurnstileKey(k => k + 1);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 lg:p-12 font-sans text-slate-50 relative overflow-hidden">
            {/* Ambient background blobs */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/30 blur-[120px] rounded-full animate-blob" />
                <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[100px] rounded-full animate-blob [animation-delay:2s]" />
                <div className="absolute bottom-[-10%] left-[20%] w-[45%] h-[45%] bg-indigo-600/20 blur-[120px] rounded-full animate-blob [animation-delay:4s]" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-xl relative z-10"
            >
                {/* Logo */}
                <div className="flex items-center justify-center gap-3 mb-10">
                    <div className="w-12 h-12 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl flex items-center justify-center shadow-lg">
                        <Wallet className="text-white w-7 h-7" />
                    </div>
                    <span className="font-bold text-2xl tracking-tight text-white">KarinBank</span>
                </div>

                <Card className="shadow-2xl shadow-purple-600/20 backdrop-blur-md bg-white/10 border border-white/20">
                    <div className="space-y-8">
                        <div className="text-center space-y-2">
                            <h1 className="text-3xl font-bold tracking-tight text-white">Create Account</h1>
                            <p className="text-white/60 font-medium">Join us to experience premium banking.</p>
                        </div>

                        {error && (
                            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-xl text-sm font-bold flex items-center gap-2">
                                <ShieldCheck className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <Input
                                    label="First Name"
                                    placeholder="John"
                                    required
                                    leftElement={<User className="w-4 h-4" />}
                                    value={formData.first_name}
                                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                />
                                <Input
                                    label="Last Name"
                                    placeholder="Doe"
                                    required
                                    value={formData.last_name}
                                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                />
                            </div>

                            <Input
                                label="Email Address"
                                type="email"
                                placeholder="john@example.com"
                                required
                                leftElement={<Mail className="w-4 h-4" />}
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            />

                            <div className="relative group">
                                <Input
                                    label="Password"
                                    type="text"
                                    placeholder="••••••••••••••••"
                                    required
                                    leftElement={<Key className="w-4 h-4" />}
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    rightElement={
                                        <button
                                            type="button"
                                            onClick={generatePassword}
                                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors group/btn"
                                            title="Generate Secure Password"
                                        >
                                            <RefreshCw className="w-4 h-4 text-gray-400 group-hover/btn:text-black group-hover/btn:rotate-180 transition-all duration-500" />
                                        </button>
                                    }
                                    helperText="Min 8 characters. Use 'Generate' for a strong one."
                                />
                            </div>

                            <Button
                                type="submit"
                                className="w-full"
                                loading={loading}
                                size="lg"
                                disabled={!captchaToken}
                            >
                                Register Now
                            </Button>

                            <Turnstile
                                key={turnstileKey}
                                onVerify={(token) => setCaptchaToken(token)}
                                onError={() => setError('Captcha failed to load.')}
                                onExpire={() => setCaptchaToken(null)}
                            />
                        </form>

                        <div className="text-center pt-2">
                            <p className="text-white/60 text-sm font-medium">
                                Already have an account?{' '}
                                <Link href="/auth/login" className="text-white font-bold hover:underline underline-offset-4">
                                    Sign In
                                </Link>
                            </p>
                        </div>
                    </div>
                </Card>

                {/* Trust Footer */}
                <div className="mt-12 flex items-center justify-center gap-8 opacity-50 hover:opacity-100 transition-all duration-500">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-white/40">
                        <ShieldCheck className="w-4 h-4" />
                        SECURE AES-256
                    </div>
                    <div className="w-px h-4 bg-white/20" />
                    <div className="text-xs font-bold uppercase tracking-widest text-white/40">
                        TRUSTED BY 1M+
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
