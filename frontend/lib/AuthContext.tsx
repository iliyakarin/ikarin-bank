"use client";
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    backup_email?: string;
    role: string;
}

interface Settings {
    use24Hour: boolean;
    useEUDates: boolean;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => Promise<void>;
    logout: () => void;
    isLoading: boolean;
    settings: Settings;
    updateSettings: (newSettings: Partial<Settings>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [settings, setSettings] = useState<Settings>({ use24Hour: false, useEUDates: false });
    const router = useRouter();

    useEffect(() => {
        const savedSettings = localStorage.getItem('bank_settings');
        if (savedSettings) {
            try {
                setSettings(JSON.parse(savedSettings));
            } catch (e) { }
        }

        const savedToken = localStorage.getItem('bank_token');
        if (savedToken) {
            setToken(savedToken);
            fetchUser(savedToken);
        } else {
            setIsLoading(false);
        }
    }, []);

    const fetchUser = async (authToken: string) => {
        try {
            const res = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            if (res.ok) {
                const userData = await res.json();
                setUser(userData);
            } else {
                logout();
            }
        } catch (err) {
            console.error("Failed to fetch user", err);
            logout();
        } finally {
            setIsLoading(false);
        }
    };

    const login = async (newToken: string) => {
        localStorage.setItem('bank_token', newToken);
        setToken(newToken);
        await fetchUser(newToken);
        router.push('/client');
    };

    const logout = async () => {
        // Call server-side logout to record the event
        try {
            if (token) {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                });
            }
        } catch (err) {
            console.error("Server logout call failed", err);
        }
        // Always clear client state regardless of server response
        localStorage.removeItem('bank_token');
        setToken(null);
        setUser(null);
        router.push('/auth/login');
    };

    const updateSettings = (newSettings: Partial<Settings>) => {
        const updated = { ...settings, ...newSettings };
        setSettings(updated);
        localStorage.setItem('bank_settings', JSON.stringify(updated));
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading, settings, updateSettings }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
