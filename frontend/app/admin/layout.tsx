import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AdminWrapper } from './AdminWrapper';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Mission Control | Karin Bank Admin",
    description: "High-density observability and pressure testing portal",
};

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className={inter.className}>
            <AdminWrapper>{children}</AdminWrapper>
        </div>
    );
}
