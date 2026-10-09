import importlib.util
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings


class ProductionConfigurationTests(SimpleTestCase):
    def environment(self):
        return {
            'DJANGO_ENV': 'production', 'DJANGO_SECRET_KEY': secrets.token_urlsafe(64),
            'DJANGO_ALLOWED_HOSTS': 'demo.example.com', 'DB_NAME': 'test', 'DB_USER': 'test',
            'DB_PASSWORD': secrets.token_urlsafe(32), 'DB_HOST': 'db.internal',
        }

    def load(self, env):
        with patch.dict(os.environ, env, clear=True):
            spec = importlib.util.spec_from_file_location('config._deployment_test_settings', Path(__file__).resolve().parent.parent / 'config' / 'settings.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return vars(module)

    def test_production_requires_private_secret_explicit_hosts_and_postgres(self):
        for changes in [
            {'DJANGO_SECRET_KEY': ''}, {'DJANGO_SECRET_KEY': 'django-insecure-example'},
            {'DJANGO_ALLOWED_HOSTS': ''}, {'DJANGO_ALLOWED_HOSTS': '*'},
            {'DJANGO_ALLOWED_HOSTS': '.example.com'}, {'DB_ENGINE': 'sqlite'},
            {'DB_PASSWORD': ''}, {'DB_HOST': ''}, {'DJANGO_ENV': 'prod'},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ImproperlyConfigured):
                self.load(self.environment() | changes)

    def test_production_security_and_shared_cache_defaults(self):
        settings = self.load(self.environment())
        self.assertFalse(settings['DEBUG'])
        for name in ['SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE']:
            self.assertTrue(settings[name], name)
        self.assertEqual(settings['DATABASES']['default']['OPTIONS']['sslmode'], 'require')
        self.assertEqual(settings['CACHES']['default']['BACKEND'], 'django.core.cache.backends.db.DatabaseCache')
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', settings)

    def test_proxy_identity_requires_explicit_trust(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(self.environment() | {'DJANGO_PROXY_COUNT': '1'})
        settings = self.load(self.environment() | {'DJANGO_TRUST_PROXY': 'true', 'DJANGO_PROXY_COUNT': '1'})
        self.assertEqual(settings['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertEqual(settings['REST_FRAMEWORK']['NUM_PROXIES'], 1)

    def test_development_remains_local_sqlite(self):
        settings = self.load({})
        self.assertTrue(settings['DEBUG'])
        self.assertEqual(settings['DATABASES']['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertFalse(settings['SESSION_COOKIE_SECURE'])


class DeploymentEndpointTests(TestCase):
    def test_health_checks_database_without_exposing_details(self):
        self.assertEqual(self.client.get('/health/').json(), {'status': 'ok'})
        with patch('config.views.connection.cursor', side_effect=OperationalError('private database details')):
            response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
        self.assertIn('no-store', response['Cache-Control'])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['demo.example.com'], SECURE_SSL_REDIRECT=True,
                       SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
                       SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_https_redirect_host_validation_and_secure_session_bootstrap(self):
        response = self.client.get('/auth/session', HTTP_HOST='demo.example.com')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://demo.example.com/auth/session')
        self.assertEqual(self.client.get('/health/', HTTP_HOST='demo.example.com').status_code, 200)
        response = self.client.get('/auth/session', HTTP_HOST='demo.example.com', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies['security_dashboard_csrf']['secure'])
        response = self.client.get('/health/', HTTP_HOST='untrusted.example.com', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 400)

    def test_frontend_entry_is_uncached_and_does_not_swallow_api_routes(self):
        with TemporaryDirectory() as directory, override_settings(FRONTEND_DIST=Path(directory)):
            self.assertEqual(self.client.get('/').status_code, 503)
            Path(directory, 'index.html').write_text('<html>Built workspace</html>')
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(b''.join(response.streaming_content), b'<html>Built workspace</html>')
            self.assertEqual(self.client.get('/events').status_code, 403)
            self.assertEqual(self.client.get('/unknown-api').status_code, 404)
