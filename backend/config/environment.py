"""Small, strict environment readers shared by deployment settings."""
import os

from django.core.exceptions import ImproperlyConfigured


def boolean(name, default=False):
    value = os.environ.get(name, str(default)).strip().lower()
    if value not in {'true', 'false', '1', '0'}:
        raise ImproperlyConfigured(f'{name} must be true or false.')
    return value in {'true', '1'}


def csv(name):
    return [value.strip() for value in os.environ.get(name, '').split(',') if value.strip()]


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} is required in production.')
    return value
