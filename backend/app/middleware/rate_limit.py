"""
Rate limiting middleware for API protection.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
import time
from collections import defaultdict
import asyncio
from loguru import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.

    Limits requests per IP address to prevent abuse.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        exclude_paths: list = None,
    ):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute per IP
            burst_size: Maximum burst size (concurrent requests)
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]

        # Token bucket per IP address
        # Format: {ip: (tokens, last_update_time)}
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (burst_size, time.time())
        )

        # Cleanup task
        self._cleanup_task = None

    async def dispatch(self, request: Request, call_next):
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        allowed, retry_after = self._check_rate_limit(client_ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        remaining = int(self.buckets[client_ip][0])
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.

        Args:
            request: Incoming request

        Returns:
            Client IP address
        """
        # Check for forwarded headers (when behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Uses token bucket algorithm:
        - Tokens are added at a constant rate (requests_per_minute / 60)
        - Each request consumes one token
        - Burst allows temporary spikes up to burst_size

        Args:
            client_ip: Client IP address

        Returns:
            (allowed, retry_after_seconds)
        """
        current_time = time.time()
        tokens, last_update = self.buckets[client_ip]

        # Calculate tokens to add since last update
        time_passed = current_time - last_update
        tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
        tokens = min(self.burst_size, tokens + tokens_to_add)

        # Check if we have tokens available
        if tokens >= 1:
            # Consume one token
            self.buckets[client_ip] = (tokens - 1, current_time)
            return True, 0
        else:
            # Calculate retry after time
            tokens_needed = 1 - tokens
            retry_after = int(tokens_needed / (self.requests_per_minute / 60.0)) + 1
            return False, retry_after

    async def cleanup_old_buckets(self):
        """
        Periodically clean up old bucket entries to prevent memory leaks.
        """
        while True:
            await asyncio.sleep(300)  # Clean every 5 minutes

            current_time = time.time()
            old_ips = []

            for ip, (tokens, last_update) in self.buckets.items():
                # Remove entries not accessed in last 10 minutes
                if current_time - last_update > 600:
                    old_ips.append(ip)

            for ip in old_ips:
                del self.buckets[ip]

            if old_ips:
                logger.debug(f"Cleaned up {len(old_ips)} old rate limit entries")


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Stricter rate limiting for authentication endpoints to prevent brute force.
    """

    def __init__(
        self,
        app,
        login_attempts_per_minute: int = 5,
        register_attempts_per_minute: int = 3,
    ):
        """
        Initialize auth rate limiter.

        Args:
            app: FastAPI application
            login_attempts_per_minute: Max login attempts per minute
            register_attempts_per_minute: Max registration attempts per minute
        """
        super().__init__(app)
        self.login_attempts_per_minute = login_attempts_per_minute
        self.register_attempts_per_minute = register_attempts_per_minute

        # Separate buckets for different endpoints
        self.login_buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (login_attempts_per_minute, time.time())
        )
        self.register_buckets: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (register_attempts_per_minute, time.time())
        )

    async def dispatch(self, request: Request, call_next):
        """Process auth requests with strict rate limiting."""
        path = request.url.path

        # Only apply to auth endpoints
        if not path.startswith("/api/v1/auth/"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Apply different limits for different endpoints
        if "login" in path:
            allowed, retry_after = self._check_login_limit(client_ip)
        elif "register" in path:
            allowed, retry_after = self._check_register_limit(client_ip)
        else:
            # Other auth endpoints (refresh, etc.) use standard limits
            return await call_next(request)

        if not allowed:
            logger.warning(f"Auth rate limit exceeded for IP: {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many authentication attempts. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_login_limit(self, client_ip: str) -> Tuple[bool, int]:
        """Check login rate limit."""
        return self._check_bucket(
            self.login_buckets,
            client_ip,
            self.login_attempts_per_minute
        )

    def _check_register_limit(self, client_ip: str) -> Tuple[bool, int]:
        """Check registration rate limit."""
        return self._check_bucket(
            self.register_buckets,
            client_ip,
            self.register_attempts_per_minute
        )

    def _check_bucket(
        self,
        buckets: Dict,
        client_ip: str,
        rate: int
    ) -> Tuple[bool, int]:
        """Check rate limit for a specific bucket."""
        current_time = time.time()
        tokens, last_update = buckets[client_ip]

        # Calculate tokens to add
        time_passed = current_time - last_update
        tokens_to_add = time_passed * (rate / 60.0)
        tokens = min(rate, tokens + tokens_to_add)

        # Check if allowed
        if tokens >= 1:
            buckets[client_ip] = (tokens - 1, current_time)
            return True, 0
        else:
            tokens_needed = 1 - tokens
            retry_after = int(tokens_needed / (rate / 60.0)) + 1
            return False, retry_after
