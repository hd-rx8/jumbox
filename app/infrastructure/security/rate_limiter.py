from __future__ import annotations

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window token rate limiter to protect public endpoints against
    credential stuffing, login brute-force, and share code enumeration.
    """

    def __init__(self, app, limits: dict[str, tuple[int, int]] | None = None):
        super().__init__(app)
        # route_prefix -> (max_requests, window_seconds)
        self.limits = limits or {
            "/api/v1/auth/login": (10, 60),
            "/api/v1/auth/register": (10, 60),
            "/api/v1/sessions/code": (30, 60),
        }
        self._history: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "127.0.0.1")
        path = request.url.path
        now = time.time()

        for route_prefix, (max_reqs, window) in self.limits.items():
            if path.startswith(route_prefix):
                key = f"{client_ip}:{route_prefix}"
                timestamps = [t for t in self._history[key] if now - t < window]
                if len(timestamps) >= max_reqs:
                    retry_after = int(window - (now - timestamps[0]))
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please try again later."},
                        headers={"Retry-After": str(max(1, retry_after))},
                    )
                timestamps.append(now)
                self._history[key] = timestamps
                break

        return await call_next(request)
