import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";
import { headers } from "next/headers";
import { AuthProvider } from "@/lib/AuthContext";
import Script from "next/script";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Karin Bank | Premium Fintech",
    description: "Experience the future of personal finance with high-end glassmorphism design.",
    icons: {
        icon: [
            { url: "/icon.png", type: "image/png" },
        ],
        shortcut: ["/icon.png"],
        apple: [
            { url: "/icon.png", sizes: "180x180", type: "image/png" },
        ],
    },
};

export const dynamic = 'force-dynamic';

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const nonce = (await headers()).get("x-csp-nonce") || "";
    return (
        <html lang="en" className="dark">
            <body className={`${inter.className} bg-slate-950 text-slate-50 antialiased`}>
                <Script
                    src="https://challenges.cloudflare.com/turnstile/v0/api.js"
                    strategy="afterInteractive"
                />
                <Script
                    id="turnstile-site-key-injection"
                    strategy="beforeInteractive"
                    nonce={nonce}
                    dangerouslySetInnerHTML={{
                        __html: `window.TURNSTILE_SITE_KEY = "${process.env.TURNSTILE_SITE_KEY || process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || ''}";`
                    }}
                />
                <ErrorBoundary>
                    <AuthProvider>
                        {children}
                    </AuthProvider>
                </ErrorBoundary>
            </body>
        </html>
    );
}
