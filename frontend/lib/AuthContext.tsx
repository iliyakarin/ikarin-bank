"use client";
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { User, getCurrentUser, logout as logoutApi, updatePreferences } from './api/auth';

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
            fetchUser();
        } else {
            setIsLoading(false);
        }
    }, []);

    const fetchUser = async () => {
        try {
            const userData = await getCurrentUser();
            setUser(userData);
            // Sync settings from db
            setSettings({
                use24Hour: userData.time_format === '24h',
                useEUDates: userData.date_format === 'EU'
            });
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
        await fetchUser();
        router.push('/client');
    };

    const logout = async () => {
        // Call server-side logout to record the event
        try {
            await logoutApi();
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
                await updatePreferences({
                    time_format: updated.use24Hour ? '24h' : '12h',
                    date_format: updated.useEUDates ? 'EU' : 'US'
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
