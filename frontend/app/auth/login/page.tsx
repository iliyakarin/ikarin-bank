"use client";
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Wallet, Key, Mail, ShieldCheck, ArrowRight } from 'lucide-react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Card from '@/components/ui/Card';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import Turnstile from '@/components/ui/Turnstile';

export default function LoginPage() {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [captchaToken, setCaptchaToken] = useState<string | null>(null);
    const { login } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const params = new URLSearchParams();
            params.append('username', formData.email);
            params.append('password', formData.password);
            if (captchaToken) {
                params.append('captcha_token', captchaToken);
            }

            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params,
            });

            if (res.ok) {
                const data = await res.json();
                await login(data.access_token);
            } else if (res.status === 401) {
                setError('Invalid email or password');
            } else if (res.status === 400) {
                const data = await res.json();
                setError(data.detail || 'Invalid request');
            } else {
                setError('Server error (500). Please check backend logs.');
            }
        } catch (err) {
            setError('Connection error. Is the API running?');
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
                className="w-full max-w-lg relative z-10"
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
                            <h1 className="text-3xl font-bold tracking-tight text-white">Welcome Back</h1>
                            <p className="text-white/60 font-medium">Please enter your details to sign in.</p>
                        </div>

                        {error && (
                            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-xl text-sm font-bold flex items-center gap-2">
                                <ShieldCheck className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-6">
                            <Input
                                label="Email Address"
                                type="email"
                                placeholder="john@example.com"
                                required
                                leftElement={<Mail className="w-4 h-4" />}
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            />

                            <Input
                                label="Password"
                                type="password"
                                placeholder="••••••••"
                                required
                                leftElement={<Key className="w-4 h-4" />}
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            />

                            <Button
                                type="submit"
                                className="w-full"
                                loading={loading}
                                size="lg"
                                disabled={!captchaToken}
                            >
                                <span className="flex items-center gap-2">
                                    Sign In <ArrowRight className="w-4 h-4" />
                                </span>
                            </Button>

                            <Turnstile
                                onVerify={(token) => setCaptchaToken(token)}
                                onError={() => setError('Captcha failed to load.')}
                                onExpire={() => setCaptchaToken(null)}
                            />
                        </form>

                        <div className="text-center pt-2">
                            <p className="text-white/60 text-sm font-medium">
                                Don't have an account?{' '}
                                <Link href="/auth/register" className="text-white font-bold hover:underline underline-offset-4">
                                    Sign Up
                                </Link>
                            </p>
                        </div>
                    </div>
                </Card>
            </motion.div>
        </div >
    );
}
