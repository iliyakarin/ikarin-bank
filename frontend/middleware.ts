import { NextResponse } from "next/server";
import { headers } from "next/headers";

export function middleware(request: Request) {
    const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

    const csp = [
        `default-src 'self'`,
        `script-src 'self' 'nonce-${nonce}' https://challenges.cloudflare.com`,
        `style-src 'self' 'nonce-${nonce}'`,
        `img-src 'self' data:`,
        `connect-src 'self' https://challenges.cloudflare.com`,
        `frame-src 'self' https://challenges.cloudflare.com`,
        `frame-ancestors 'none'`,
        `form-action 'self'`,
    ].join("; ");

    const response = NextResponse.next();
    response.headers.set("Content-Security-Policy", csp);
    response.headers.set("X-CSP-Nonce", nonce);

    return response;
}

export const config = {
    matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.png).*)"],
};
