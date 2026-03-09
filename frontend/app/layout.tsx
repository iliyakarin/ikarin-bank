import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Karin Bank | Premium Fintech",
    description: "Experience the future of personal finance with high-end glassmorphism design.",
};

import { AuthProvider } from "@/lib/AuthContext";

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <head>
                <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
            </head>
            <body className={`${inter.className} bg-slate-950 text-slate-50 antialiased`}>
                <ErrorBoundary>
                    <AuthProvider>
                        {children}
                    </AuthProvider>
                </ErrorBoundary>
            </body>
        </html>
    );
}
