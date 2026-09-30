"""
Django settings for exam_prep project (ExamHub24).
"""
import os
from pathlib import Path
from datetime import timedelta

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
# Read .env file if present
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-in-production-please')

DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# CSRF: needed because Django checks the request's Origin/Referer against this list.
# Add your real domain(s) here via .env, e.g. CSRF_TRUSTED_ORIGINS=https://yourusername.pythonanywhere.com
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Security hardening — only enforced when DEBUG=False (production), so local dev over
# plain http:// still works normally.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # PythonAnywhere and most PaaS providers terminate SSL at a proxy and forward plain
    # HTTP internally — this tells Django to trust the proxy's "X-Forwarded-Proto" header
    # instead of redirect-looping forever.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',

    # ExamHub24 apps
    'core',
    'accounts',
    'exams',
    'questions',
    'mock_tests',
    'results',
    'current_affairs',
    'dashboard',
    'payments',
    'subscriptions',
    'study_material',
    'notifications',
    'analytics',
    'discussion',
    'institutions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # must come before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'exam_prep.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'exam_prep.wsgi.application'
ASGI_APPLICATION = 'exam_prep.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Default: SQLite (works out of the box for local dev).
# For MySQL/PostgreSQL, set DATABASE_URL in your .env, e.g.:
#   DATABASE_URL=postgres://user:password@localhost:5432/examhub24
#   DATABASE_URL=mysql://user:password@localhost:3306/examhub24
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'core:home'

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'

# Multi-language groundwork: infrastructure is wired up (LocaleMiddleware, language
# switcher in the navbar, /i18n/setlang/ URL) but the actual Hindi translations still
# need to be written — see README "Multi-language support" section for the workflow
# (django-admin makemessages / compilemessages).
LANGUAGES = [
    ('en', 'English'),
    ('hi', 'हिन्दी (Hindi)'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
# Set REDIS_URL in .env (e.g. redis://127.0.0.1:6379/1, or a managed Redis URL) for a
# real shared cache across worker processes — required for rate-limiting (core/throttle.py)
# and the leaderboard/homepage caching below to work correctly under multiple processes/
# workers. Without it, falls back to Django's in-memory cache, which is fine for local
# development and single-process deployments (e.g. a single PythonAnywhere web worker)
# but each process gets its own cache, so counters/cached data won't be shared.
REDIS_URL = env('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ---------------------------------------------------------------------------
# Crispy Forms
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ---------------------------------------------------------------------------
# Email (console backend for dev; configure SMTP for production)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='ExamHub24 <no-reply@examhub24.com>')

# ---------------------------------------------------------------------------
# Payment gateway (Razorpay) — set real keys in .env for production
# ---------------------------------------------------------------------------
RAZORPAY_KEY_ID = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = env('RAZORPAY_KEY_SECRET', default='')

# ---------------------------------------------------------------------------
# Site-wide constants
# ---------------------------------------------------------------------------
SITE_NAME = 'ExamHub24'

# Configurable admin URL — set ADMIN_URL in .env for production (e.g. ADMIN_URL=eh-manage/)
# so the default '/admin/' path, a common target for automated bots, isn't predictable.
ADMIN_URL = env('ADMIN_URL', default='admin/')
OTP_VALIDITY_MINUTES = 10

# ---------------------------------------------------------------------------
# Error monitoring (Sentry) — completely optional. Leave SENTRY_DSN blank in .env
# and this block does nothing (no package required, no behavior change).
# Sign up free at https://sentry.io, create a Django project, copy its DSN into
# .env, and `pip install sentry-sdk` — errors will then show up in the Sentry
# dashboard with full tracebacks instead of only living in server logs.
# ---------------------------------------------------------------------------
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.2,  # 20% of requests get performance tracing; raise/lower as needed
            send_default_pii=False,  # don't send user emails/IPs to Sentry by default
            environment='production' if not DEBUG else 'development',
        )
    except ImportError:
        # sentry-sdk not installed — SENTRY_DSN is set but the package isn't there yet.
        # Fails silently rather than crashing the whole site over a monitoring tool.
        pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Rotating file handler so log files don't grow forever and fill up disk (a real risk on
# PythonAnywhere's free tier, which has a small storage quota). Keeps 5 backup files at
# 5 MB each (25 MB total) before the oldest is discarded. Logs to console as well, which
# is what actually shows up in PythonAnywhere's error log viewer — the file handler is a
# secondary, greppable copy on disk.
LOGS_DIR = BASE_DIR / 'logs'
try:
    LOGS_DIR.mkdir(exist_ok=True)
except OSError:
    pass  # read-only filesystem or permissions issue — logging still works via console

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'examhub24.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'delay': True,  # don't open/create the file until the first log record — avoids
                             # a hard crash at startup if LOGS_DIR couldn't be created above
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            # Full tracebacks for unhandled 500 errors — the single most useful thing to
            # have logged when something breaks in production.
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
