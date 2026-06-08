"""Rate limiting utilities for protecting sensitive endpoints."""

import time
from collections import defaultdict
from threading import Lock
from typing import Callable
from functools import wraps

from fastapi import HTTPException, status, Request


class RateLimiter:
    """Simple in-memory rate limiter tracking requests per key (IP/user)."""

    def __init__(self, max_requests: int, window_seconds: int):
        """Initialize rate limiter.

        Parameters
        ----------
        max_requests
            Maximum requests allowed per window
        window_seconds
            Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed for the given key.

        Parameters
        ----------
        key
            Identifier (IP address, username, etc.)

        Returns
        -------
        bool
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        with self.lock:
            # Remove old requests outside the window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.window_seconds
            ]

            # Check if limit exceeded
            if len(self.requests[key]) >= self.max_requests:
                return False

            # Record new request
            self.requests[key].append(now)
            return True


# Rate limiters for different endpoints
login_limiter = RateLimiter(max_requests=5, window_seconds=60)  # 5 per minute
user_creation_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 per minute
api_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 per minute


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, accounting for proxies."""
    if request.headers.get("x-forwarded-for"):
        return request.headers.get("x-forwarded-for").split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limiter: RateLimiter, key_func: Callable[[Request], str] = get_client_ip):
    """Decorator to apply rate limiting to an endpoint.

    Parameters
    ----------
    limiter
        RateLimiter instance to use
    key_func
        Function to extract rate limit key from request
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (injected by FastAPI)
            request = kwargs.get("request")
            if request and isinstance(request, Request):
                key = key_func(request)
                if not limiter.is_allowed(key):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later."
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
