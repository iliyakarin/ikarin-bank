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
    time_format: string;
    date_format: string;
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
            const res = await fetch('/api/v1/me', {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            if (res.ok) {
                const userData = await res.json();
                setUser(userData);
                // Sync settings from db
                setSettings({
                    use24Hour: userData.time_format === '24h',
                    useEUDates: userData.date_format === 'EU'
                });
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
                await fetch('/api/v1/logout', {
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

    const updateSettings = async (newSettings: Partial<Settings>) => {
        const updated = { ...settings, ...newSettings };
        setSettings(updated);

        // Persist to DB if logged in
        if (token) {
            try {
                await fetch('/api/v1/users/me/preferences', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        time_format: updated.use24Hour ? '24h' : '12h',
                        date_format: updated.useEUDates ? 'EU' : 'US'
                    })
                });
            } catch (err) {
                console.error("Failed to persist settings", err);
            }
        }
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
