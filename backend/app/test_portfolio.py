import os
import secrets
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .accounts import set_role
from .models import DemoDataset, DetectionFinding, Investigation, LoginEvent
from .permissions import role_for


class PortfolioProvisionTests(TestCase):
    def provision(self, **changes):
        env = {'PORTFOLIO_ADMIN_PASSWORD': secrets.token_urlsafe(32), 'PORTFOLIO_VIEWER_PASSWORD': secrets.token_urlsafe(32)} | changes
        with patch.dict(os.environ, env):
            call_command('provision_portfolio', stdout=StringIO())
        return env

    def test_demo_has_complete_workflow_and_read_only_visitor(self):
        env = self.provision()
        self.assertEqual(LoginEvent.objects.count(), 71)
        self.assertEqual(DetectionFinding.objects.count(), 3)
        self.assertEqual(set(Investigation.objects.values_list('status', flat=True)), {'new', 'investigating', 'resolved'})
        User = get_user_model()
        viewer = User.objects.get(username='portfolio-viewer')
        self.assertEqual(role_for(viewer), 'viewer')
        self.assertTrue(viewer.check_password(env['PORTFOLIO_VIEWER_PASSWORD']))
        self.assertFalse(User.objects.get(username='demo-analyst').has_usable_password())
        self.assertFalse(User.objects.get(username='portfolio-admin').check_password(env['PORTFOLIO_VIEWER_PASSWORD']))
        self.assertFalse(Investigation.objects.filter(owner_user__isnull=True).exists())
        case = Investigation.objects.get(status='resolved')
        self.assertTrue(case.notes.exists())
        self.assertTrue(case.history.filter(action='resolved').exists())
        client = APIClient()
        client.force_authenticate(viewer)
        self.assertEqual(client.get('/investigations').status_code, 200)
        self.assertEqual(client.post('/investigations', {'finding_id': case.finding_id}, format='json').status_code, 403)
        self.assertEqual(client.get('/users').status_code, 403)

    def test_restart_keeps_counts_notes_and_passwords(self):
        env = self.provision()
        case = Investigation.objects.get(status='investigating')
        case.notes.create(author='demo-analyst', author_user=case.owner_user, text='Retain this analyst note.')
        counts = (LoginEvent.objects.count(), DetectionFinding.objects.count(), Investigation.objects.count())
        self.provision()
        self.assertEqual(counts, (LoginEvent.objects.count(), DetectionFinding.objects.count(), Investigation.objects.count()))
        self.assertTrue(case.notes.filter(text='Retain this analyst note.').exists())
        self.assertTrue(get_user_model().objects.get(username='portfolio-viewer').check_password(env['PORTFOLIO_VIEWER_PASSWORD']))
        self.assertEqual(DemoDataset.objects.count(), 1)

    def test_existing_database_is_not_modified(self):
        event = LoginEvent.objects.create(ip_address='198.51.100.8', success=True)
        with self.assertRaises(CommandError):
            self.provision()
        self.assertEqual(list(LoginEvent.objects.values_list('id', flat=True)), [event.id])
        self.assertFalse(DemoDataset.objects.exists())
        self.assertFalse(get_user_model().objects.exists())

    def test_missing_or_shared_passwords_roll_back_provisioning(self):
        shared = secrets.token_urlsafe(32)
        for changes in [{'PORTFOLIO_VIEWER_PASSWORD': ''}, {'PORTFOLIO_ADMIN_PASSWORD': shared, 'PORTFOLIO_VIEWER_PASSWORD': shared}]:
            with self.subTest(changes=list(changes)), self.assertRaises(CommandError):
                self.provision(**changes)
            self.assertFalse(DemoDataset.objects.exists())
            self.assertFalse(get_user_model().objects.exists())
            self.assertFalse(LoginEvent.objects.exists())




@override_settings(PORTFOLIO_MODE=True)
class PortfolioGuestTests(TestCase):
    def setUp(self):
        cache.clear()
        DemoDataset.objects.create(key='portfolio-v1')
        self.viewer = get_user_model().objects.create_user(username='portfolio-viewer')
        set_role(self.viewer, 'viewer')
        self.client = APIClient(enforce_csrf_checks=True)

    def explore(self, client=None):
        client = client or self.client
        token = client.get('/auth/session').json()['csrf_token']
        return client.post('/auth/demo-login', {}, format='json', HTTP_X_CSRFTOKEN=token)

    def test_public_entry_is_csrf_protected_and_read_only(self):
        self.assertEqual(self.client.post('/auth/demo-login').status_code, 403)
        response = self.explore()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], 'viewer')
        self.assertTrue(response.json()['demo']['available'])
        self.assertTrue(self.client.session['portfolio_guest'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get('/events').status_code, 200)
        self.assertEqual(self.client.get('/users').status_code, 403)
        token = response.json()['csrf_token']
        for path in ['/investigations', '/login-attempt', '/users']:
            self.assertEqual(self.client.post(path, {}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 403)
        logout = self.client.post('/auth/logout', {}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertIsNone(logout.json()['user'])
        self.assertEqual(self.client.get('/events').status_code, 403)

    def test_mode_is_opt_in_and_requires_initialized_viewer(self):
        with override_settings(PORTFOLIO_MODE=False):
            self.assertIsNone(self.client.get('/auth/session').json()['demo'])
            self.assertEqual(self.explore().status_code, 404)
        DemoDataset.objects.all().delete()
        self.assertFalse(self.client.get('/auth/session').json()['demo']['available'])
        self.assertEqual(self.explore().status_code, 404)

    def test_disabled_or_promoted_account_cannot_enter(self):
        self.viewer.is_active = False
        self.viewer.save()
        self.assertEqual(self.explore().status_code, 404)
        self.viewer.is_active = True
        set_role(self.viewer, 'analyst')
        self.assertEqual(self.explore().status_code, 404)

    def test_existing_guest_session_is_revoked_on_promotion(self):
        self.explore()
        set_role(self.viewer, 'admin')
        self.assertIsNone(self.client.get('/auth/session').json()['user'])
        self.assertEqual(self.client.get('/events').status_code, 403)

    def test_existing_guest_session_is_revoked_when_mode_disabled(self):
        self.explore()
        with override_settings(PORTFOLIO_MODE=False):
            self.assertEqual(self.client.get('/events').status_code, 403)
            self.assertIsNone(self.client.get('/auth/session').json()['user'])

    def test_public_entry_preserves_staff_session_and_blocks_promotion(self):
        admin = get_user_model().objects.create_user(username='private-admin', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.explore().status_code, 409)
        self.assertEqual(self.client.get('/auth/session').json()['user']['username'], 'private-admin')
        token = self.client.get('/auth/session').json()['csrf_token']
        response = self.client.patch(f'/users/{self.viewer.pk}', {'role': 'admin'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.viewer.refresh_from_db()
        self.assertEqual(role_for(self.viewer), 'viewer')

    def test_public_entry_is_rate_limited(self):
        for _ in range(10):
            self.assertEqual(self.explore(APIClient(enforce_csrf_checks=True)).status_code, 200)
        response = self.explore(APIClient(enforce_csrf_checks=True))
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
