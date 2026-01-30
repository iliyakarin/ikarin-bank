import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import { AdminWrapper } from './AdminWrapper';

const mono = JetBrains_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Mission Control | Karin Bank Admin",
    description: "High-density observability and pressure testing portal",
};

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <AdminWrapper>{children}</AdminWrapper>;
}