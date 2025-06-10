"""
Dashboard Optimization Settings
Configuration for materialized views and performance optimizations
"""

import os
from .base import *

# Dashboard optimization settings
DASHBOARD_OPTIMIZATION = {
    'ENABLED': os.environ.get('DASHBOARD_OPTIMIZATION_ENABLED', 'True').lower() == 'true',
    'AUTO_REFRESH': os.environ.get('DASHBOARD_AUTO_REFRESH', 'True').lower() == 'true',
    'REFRESH_INTERVAL': int(os.environ.get('DASHBOARD_REFRESH_INTERVAL', '3600')),  # 1 hour default
    'CONCURRENT_REFRESH': os.environ.get('DASHBOARD_CONCURRENT_REFRESH', 'True').lower() == 'true',
}

# Extend cache configuration for dashboard
CACHES['dashboard'] = {
    'BACKEND': os.environ.get('DASHBOARD_CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
    'LOCATION': os.environ.get('DASHBOARD_CACHE_LOCATION', 'dashboard-cache'),
    'KEY_PREFIX': 'dash',
    'TIMEOUT': 300,  # 5 minutes default
    'OPTIONS': {
        'MAX_ENTRIES': int(os.environ.get('DASHBOARD_CACHE_MAX_ENTRIES', '10000')),
    }
}

# Redis configuration for production (if REDIS_URL is set)
if os.environ.get('REDIS_URL'):
    CACHES['dashboard'] = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'KEY_PREFIX': 'dash',
        'TIMEOUT': 300,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
        }
    }

# GraphQL caching for optimized queries
# Note: DjangoDebugMiddleware is deprecated in newer versions of graphene-django
if DEBUG:
    try:
        # Test if the middleware exists before adding it
        from graphene_django.debug.middleware import DjangoDebugMiddleware
        GRAPHENE['MIDDLEWARE'].append('graphene_django.debug.middleware.DjangoDebugMiddleware')
    except ImportError:
        # Middleware not available in this version
        pass

# Add cache headers for dashboard endpoints
DASHBOARD_CACHE_HEADERS = {
    'optimized_dashboard_summary': {'max-age': 300},  # 5 minutes
    'optimized_beneficiary_breakdown': {'max-age': 600},  # 10 minutes
    'optimized_transfer_performance': {'max-age': 600},  # 10 minutes
    'optimized_quarterly_trends': {'max-age': 1800},  # 30 minutes
    'optimized_grievance_dashboard': {'max-age': 300},  # 5 minutes
}

# Database optimization for materialized views
if 'postgresql' in DATABASES['default']['ENGINE']:
    # PostgreSQL-specific optimizations
    DATABASES['default']['OPTIONS'] = DATABASES['default'].get('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        'connect_timeout': 30,
        'options': '-c statement_timeout=300000'  # 5 minutes for long queries
    })

# Logging for dashboard optimization
LOGGING['loggers']['merankabandi.dashboard'] = {
    'handlers': ['db-queries' if DEBUG else 'console'],
    'level': 'INFO',
    'propagate': False,
}

# Performance monitoring
if os.environ.get('DASHBOARD_PERFORMANCE_MONITORING', 'False').lower() == 'true':
    MIDDLEWARE.append('merankabandi.middleware.DashboardPerformanceMiddleware')

# Celery tasks for dashboard refresh (if Celery is configured)
if 'CELERY_BROKER_URL' in os.environ:
    from celery.schedules import crontab
    
    # Initialize CELERY_BEAT_SCHEDULE if it doesn't exist
    if 'CELERY_BEAT_SCHEDULE' not in globals():
        CELERY_BEAT_SCHEDULE = {}
    
    CELERY_BEAT_SCHEDULE.update({
        'refresh-dashboard-views': {
            'task': 'merankabandi.tasks.refresh_dashboard_views',
            'schedule': crontab(minute=0),  # Every hour
            'options': {'queue': 'dashboard'}
        },
    })