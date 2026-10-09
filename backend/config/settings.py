"""Local defaults and fail-closed production configuration for the workspace."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .environment import boolean, csv, required

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')
if ENVIRONMENT not in {'development', 'production'}:
    raise ImproperlyConfigured('DJANGO_ENV must be development or production.')
PRODUCTION = ENVIRONMENT == 'production'
DEBUG = not PRODUCTION
DEVELOPMENT_SECRET = 'django-insecure-@34jw7w%vr1xm00f1-su2w!b281ov@d@mu*lvz%e-i1c+xyh=5'  # noqa: S105 -- Public local-development key.
SECRET_KEY = required('DJANGO_SECRET_KEY') if PRODUCTION else os.environ.get('DJANGO_SECRET_KEY', DEVELOPMENT_SECRET)
ALLOWED_HOSTS = csv('DJANGO_ALLOWED_HOSTS')
if PRODUCTION:
    if SECRET_KEY == DEVELOPMENT_SECRET or SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5:
        raise ImproperlyConfigured('Use a private random DJANGO_SECRET_KEY of at least 50 characters.')
    if not ALLOWED_HOSTS or any('*' in host or host.startswith('.') for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured('Production requires explicit DJANGO_ALLOWED_HOSTS without wildcards.')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'corsheaders',
    'app'
]

MIDDLEWARE = [
    'config.middleware.ValidateHostMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DB_ENGINE = os.environ.get('DB_ENGINE', 'postgresql' if PRODUCTION else 'sqlite')
if DB_ENGINE not in {'sqlite', 'postgresql'} or (PRODUCTION and DB_ENGINE != 'postgresql'):
    raise ImproperlyConfigured('Use DB_ENGINE=postgresql in production; sqlite is for local development.')
if DB_ENGINE == 'postgresql':
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': required('DB_NAME'), 'USER': required('DB_USER'),
        'PASSWORD': required('DB_PASSWORD'), 'HOST': required('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require'), 'connect_timeout': 5},
    }}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

# Production workers share throttle state through the database cache table.
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'workspace_cache'}} if PRODUCTION else {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

SECURE_SSL_REDIRECT = PRODUCTION
# Readiness exposes no credentials; internal HTTP probes must reach the database check.
SECURE_REDIRECT_EXEMPT = [r'^health/$']
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SECURE_HSTS_SECONDS = 31536000 if PRODUCTION else 0
# Enable only when every subdomain is HTTPS. Preload needs a separate domain decision.
SECURE_HSTS_INCLUDE_SUBDOMAINS = boolean('DJANGO_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
if boolean('DJANGO_TRUST_PROXY'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = csv('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = csv('CSRF_TRUSTED_ORIGINS')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
CSRF_FAILURE_VIEW = 'app.accounts.csrf_failure'
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_COOKIE_NAME = 'security_dashboard_session'
CSRF_COOKIE_NAME = 'security_dashboard_csrf'


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
FRONTEND_DIST = BASE_DIR.parent / 'frontend' / 'dist'
WHITENOISE_ROOT = FRONTEND_DIST
WHITENOISE_MAX_AGE = 0  # Revalidate builds; avoid stale entry documents after deployment.

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'NUM_PROXIES': int(os.environ.get('DJANGO_PROXY_COUNT', '0')),
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated', 'app.permissions.WorkspacePermission'],
    'EXCEPTION_HANDLER': 'app.permissions.exception_handler',
}

if REST_FRAMEWORK['NUM_PROXIES'] < 0 or (REST_FRAMEWORK['NUM_PROXIES'] and not boolean('DJANGO_TRUST_PROXY')):
    raise ImproperlyConfigured('DJANGO_PROXY_COUNT requires a trusted proxy and cannot be negative.')
