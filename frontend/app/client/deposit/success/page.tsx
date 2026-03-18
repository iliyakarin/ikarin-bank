import Link from "next/link";
import { CheckCircle } from "lucide-react";

export default async function DepositSuccessPage({ searchParams }: { searchParams: Promise<{ session_id?: string }> }) {
    const { session_id } = await searchParams;
    return (
        <div className="min-h-[80vh] flex items-center justify-center bg-black text-white p-8 font-sans">
            <div className="max-w-md w-full text-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="mx-auto w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center border border-emerald-500/20">
                    <CheckCircle className="h-8 w-8 text-emerald-500" />
                </div>

                <div className="space-y-3">
                    <h1 className="text-3xl font-light tracking-tight text-zinc-100">Payment Successful</h1>
                    <p className="text-zinc-500 font-light">
                        Your transaction has been securely processed and recorded on the ledger.
                    </p>
                    {session_id && (
                        <p className="text-zinc-700 text-xs font-mono pt-4 truncate">
                            Session: {session_id}
                        </p>
                    )}
                </div>

                <div className="pt-8">
                    <Link
                        href="/client"
                        className="inline-flex items-center justify-center bg-white text-black px-8 py-3 rounded-full text-sm font-medium transition-all hover:bg-zinc-200 active:scale-95 space-x-2"
                    >
                        Return to Dashboard
                    </Link>
                </div>
            </div>
        </div>
    );
}
