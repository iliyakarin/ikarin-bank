"use client";
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';

import SessionExpiryWarning from '@/components/SessionExpiryWarning';
import { User, getCurrentUser, logout as logoutApi, updatePreferences, renewToken } from './api/auth';

// Minutes before expiry at which the user is warned.
const WARNING_THRESHOLDS_MINUTES = [15, 5, 1];

/** Reads the `exp` claim (POSIX seconds) from a JWT and returns it in ms. */
function getTokenExpiryMs(token: string): number | null {
    try {
        const payload = token.split('.')[1];
        if (!payload) return null;
        const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
        const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
        const claims = JSON.parse(atob(padded));
        return typeof claims.exp === 'number' ? claims.exp * 1000 : null;
    } catch {
        return null;
    }
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

    const [warningMinutes, setWarningMinutes] = useState<number | null>(null);
    const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    // Warn ahead of expiry, then log out once the token actually expires.
    // Re-runs whenever the token changes, so a renewal reschedules cleanly.
    useEffect(() => {
        timersRef.current.forEach(clearTimeout);
        timersRef.current = [];
        setWarningMinutes(null);

        if (!token) return;
        const expiresAt = getTokenExpiryMs(token);
        if (expiresAt === null) return;

        for (const minutes of WARNING_THRESHOLDS_MINUTES) {
            const delay = expiresAt - Date.now() - minutes * 60_000;
            if (delay > 0) {
                timersRef.current.push(setTimeout(() => setWarningMinutes(minutes), delay));
            }
        }

        const untilExpiry = expiresAt - Date.now();
        if (untilExpiry > 0) {
            timersRef.current.push(setTimeout(() => logout(), untilExpiry));
        }

        return () => {
            timersRef.current.forEach(clearTimeout);
            timersRef.current = [];
        };
    }, [token]);

    const renewSession = useCallback(async () => {
        try {
            const { access_token } = await renewToken();
            localStorage.setItem('bank_token', access_token);
            setToken(access_token);
            setWarningMinutes(null);
        } catch (err) {
            console.error("Failed to renew session", err);
            logout();
        }
    }, []);

    const dismissWarning = useCallback(() => setWarningMinutes(null), []);

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading, settings, updateSettings }}>
            {warningMinutes !== null && (
                <SessionExpiryWarning
                    minutes={warningMinutes}
                    onRenew={renewSession}
                    onDismiss={dismissWarning}
                />
            )}
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
