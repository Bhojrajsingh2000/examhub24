"""
Lightweight rate-limiting for sensitive views (login, OTP, registration) using Django's
cache framework — no external package needed. Works out of the box with the default
LocMemCache; for a multi-process production deployment, point CACHES at Redis/Memcached
in settings.py so the counters are shared across worker processes.
"""
import functools

from django.core.cache import cache
from django.shortcuts import render


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(key_prefix, max_attempts=5, window_seconds=300):
    """
    Decorator for views: limits POST requests to `max_attempts` per `window_seconds`,
    keyed by client IP. On GET requests (just viewing the form) no limit is applied.

    Usage:
        @rate_limit('login', max_attempts=5, window_seconds=300)
        def my_view(request): ...
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method == 'POST':
                ip = get_client_ip(request)
                cache_key = f'ratelimit:{key_prefix}:{ip}'
                attempts = cache.get(cache_key, 0)
                if attempts >= max_attempts:
                    return render(request, 'core/rate_limited.html', {
                        'retry_minutes': window_seconds // 60,
                    }, status=429)
                cache.set(cache_key, attempts + 1, timeout=window_seconds)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
