import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import GlassNavigation from "@/components/GlassNavigation";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Karin Bank | Premium Fintech",
    description: "Experience the future of personal finance with high-end glassmorphism design.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.className} bg-slate-950 text-slate-50 antialiased`}>
                {/* Ambient background blobs */}
                <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
                    <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/30 blur-[120px] rounded-full animate-blob" />
                    <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-blue-600/20 blur-[100px] rounded-full animate-blob [animation-delay:2s]" />
                    <div className="absolute bottom-[-10%] left-[20%] w-[45%] h-[45%] bg-indigo-600/20 blur-[120px] rounded-full animate-blob [animation-delay:4s]" />
                </div>

                <div className="flex flex-col lg:flex-row min-h-screen">
                    <GlassNavigation />
                    <main className="flex-1 lg:ml-32 p-6 lg:p-12 pb-32 lg:pb-12 max-w-7xl mx-auto w-full">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    );
}
