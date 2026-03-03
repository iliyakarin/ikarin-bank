"use client";

const actions = [
    { label: 'Payments', icon: '📤', color: 'bg-blue-50 text-blue-600' },
    { label: 'Request', icon: '📥', color: 'bg-indigo-50 text-indigo-600' },
    { label: 'Pay Bills', icon: '📄', color: 'bg-purple-50 text-purple-600' },
];

export default function QuickActionsHub() {
    return (
        <div className="flex gap-4 overflow-x-auto pb-2 no-scrollbar">
            {actions.map((action) => (
                <button
                    key={action.label}
                    className="flex-1 min-w-[100px] flex flex-col items-center gap-2 p-4 rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md transition-all active:scale-95"
                >
                    <div className={`w-12 h-12 rounded-xl ${action.color} flex items-center justify-center text-2xl`}>
                        {action.icon}
                    </div>
                    <span className="text-xs font-semibold text-gray-700 whitespace-nowrap">{action.label}</span>
                </button>
            ))}
        </div>
    );
}
