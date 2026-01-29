"use client";
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { NavLink } from '@/lib/types';

const navLinks: NavLink[] = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    { name: 'Transfer', href: '/transfer', icon: '💸' },
    { name: 'Cards', href: '/cards', icon: '💳' },
    { name: 'Savings', href: '/savings', icon: '🎯' },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <>
            {/* Desktop Sidebar */}
            <aside className="hidden md:flex flex-col w-64 h-screen sticky top-0 bg-white border-r border-gray-200 p-4 transition-all duration-300">
                <div className="flex items-center gap-2 mb-10 px-2">
                    <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold">K</div>
                    <span className="text-xl font-bold text-gray-900">Karin Bank</span>
                </div>

                <nav className="flex-1 space-y-1">
                    {navLinks.map((link) => {
                        const isActive = pathname === link.href;
                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={`flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${isActive
                                        ? 'bg-primary-50 text-primary-600 font-medium'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                <span className="text-xl">{link.icon}</span>
                                <span>{link.name}</span>
                            </Link>
                        );
                    })}
                </nav>

                <div className="mt-auto p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary-200"></div>
                        <div>
                            <p className="text-sm font-medium text-gray-900">Alex Karin</p>
                            <p className="text-xs text-gray-500">Premium Member</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Mobile Bottom Nav */}
            <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex justify-around items-center h-16 px-2 z-50">
                {navLinks.map((link) => {
                    const isActive = pathname === link.href;
                    return (
                        <Link
                            key={link.href}
                            href={link.href}
                            className={`flex flex-col items-center gap-1 transition-colors ${isActive ? 'text-primary-600 font-medium' : 'text-gray-500'
                                }`}
                        >
                            <span className="text-xl">{link.icon}</span>
                            <span className="text-[10px]">{link.name}</span>
                        </Link>
                    );
                })}
            </nav>
        </>
    );
}
