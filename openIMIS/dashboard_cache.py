# Dashboard Caching Configuration
from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json

# Cache TTL for different data types (in seconds)
CACHE_TTL = {
    'dashboard_summary': 3600,      # 1 hour
    'location_performance': 7200,   # 2 hours
    'beneficiary_breakdown': 86400, # 24 hours
    'quarterly_rollup': 86400,      # 24 hours
    'activity_summary': 1800,       # 30 minutes
}

def dashboard_cache(cache_key_prefix, ttl_key='dashboard_summary'):
    """
    Decorator for caching dashboard API responses
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on request parameters
            cache_key_parts = [cache_key_prefix]
            
            # Add query parameters to cache key
            for param in sorted(request.GET.keys()):
                cache_key_parts.append(f"{param}:{request.GET.get(param)}")
            
            # Add user context if needed
            if hasattr(request, 'user') and request.user.is_authenticated:
                cache_key_parts.append(f"user:{request.user.id}")
            
            cache_key = hashlib.md5(
                "_".join(cache_key_parts).encode()
            ).hexdigest()
            
            # Try to get from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Execute the view function
            response = func(request, *args, **kwargs)
            
            # Cache the response
            ttl = CACHE_TTL.get(ttl_key, 3600)
            cache.set(cache_key, response, ttl)
            
            return response
        return wrapper
    return decorator

def invalidate_dashboard_cache(patterns=None):
    """
    Invalidate dashboard cache entries
    """
    if patterns is None:
        patterns = ['dashboard_*', 'location_*', 'beneficiary_*']
    
    for pattern in patterns:
        cache.delete_pattern(pattern)