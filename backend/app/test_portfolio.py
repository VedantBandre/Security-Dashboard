import os
import secrets
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.test import APIClient

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
