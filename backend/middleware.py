"""CSP nonce middleware — generates a per-request nonce for inline scripts.

Adds a random nonce to the Content-Security-Policy header so that
inline scripts with matching nonce attributes are allowed under the
hardened CSP (no 'unsafe-inline').
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

NONCE_HEADER = "X-CSP-Nonce"


def _generate_nonce() -> str:
    return uuid.uuid4().hex


class CspNonceMiddleware(BaseHTTPMiddleware):
    """Generates a nonce, injects it into the CSP header, and exposes
    it via the ``X-CSP-Nonce`` response header for frontend consumption.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        nonce = _generate_nonce()
        response = await call_next(request)

        # Build or append the nonce to the script-src directive.
        csp = response.headers.get("content-security-policy", "")
        if csp:
            # Replace script-src 'self' with script-src 'self' 'nonce-{nonce}'
            csp = csp.replace(
                "script-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'"
            )
            # Also allow the Cloudflare Turnstile frame/script if present
            csp = csp.replace(
                "script-src 'self' https://challenges.cloudflare.com",
                f"script-src 'self' 'nonce-{nonce}' https://challenges.cloudflare.com"
            )
        else:
            csp = f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; connect-src 'self'; img-src 'self' data:; style-src 'self'; frame-ancestors 'none'; form-action 'self';"

        response.headers["content-security-policy"] = csp
        response.headers[NONCE_HEADER] = nonce

        return response
