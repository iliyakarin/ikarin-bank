"use client";
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
    const router = useRouter();

    useEffect(() => {
        router.push('/dashboard');
    }, [router]);

    return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <div className="animate-pulse text-primary-600 font-bold">Loading your portal...</div>
        </div>
    );
}
