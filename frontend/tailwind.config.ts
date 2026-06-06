import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",

                // ── Dark palette ──
                dark: {
                    base: "#050510",
                    surface: "#0a0a1a",
                    panel: "rgba(255, 255, 255, 0.03)",
                },

                // ── Glass borders ──
                glassBorder: {
                    DEFAULT: "rgba(255, 255, 255, 0.08)",
                    strong: "rgba(255, 255, 255, 0.12)",
                    accent: "rgba(139, 92, 246, 0.25)",
                },

                primary: {
                    50: '#eff6ff',
                    100: '#dbeafe',
                    200: '#bfdbfe',
                    300: '#93c5fd',
                    400: '#60a5fa',
                    500: '#3b82f6',
                    600: '#2563eb',
                    700: '#1d4ed8',
                    800: '#1e40af',
                    900: '#1e3a8a',
                    950: '#172554',
                },
            },
            backdropBlur: {
                glass: '16px',
                elevated: '24px',
                light: '8px',
            },
            animation: {
                'blob': 'blob 7s infinite',
                'pulse-subtle': 'pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                blob: {
                    '0%': { transform: 'translate(0px, 0px) scale(1)' },
                    '33%': { transform: 'translate(30px, -50px) scale(1.1)' },
                    '66%': { transform: 'translate(-20px, 20px) scale(0.9)' },
                    '100%': { transform: 'translate(0px, 0px) scale(1)' },
                },
                'pulse-subtle': {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0.5' },
                }
            }
        },
    },
    plugins: [],
};
export default config;
