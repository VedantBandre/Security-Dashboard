from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .accounts import set_role
from .models import AccessAuditEntry, AuditEntry, InvestigationNote
from .services import ingest_login

User = get_user_model()
PASSWORD = 'Testing-workspace-9!Long'  # noqa: S105 -- Disposable test fixture, not a credential.


class AccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(username='admin-user', password=PASSWORD, is_staff=True)
        self.analyst = User.objects.create_user(username='analyst-user', password=PASSWORD)
        self.viewer = User.objects.create_user(username='viewer-user', password=PASSWORD)
        set_role(self.analyst, 'analyst')
        set_role(self.viewer, 'viewer')
        self.client = APIClient(enforce_csrf_checks=True)
        for _ in range(6):
            ingest_login({'ip': '203.0.113.90', 'username': 'reported-user', 'success': False})
        from .models import DetectionFinding
        self.finding = DetectionFinding.objects.first()

    def login(self, user=None, client=None):
        client = client or self.client
        token = client.get('/auth/session').json()['csrf_token']
        response = client.post('/auth/login', {'username': (user or self.admin).username, 'password': PASSWORD}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_X_CSRFTOKEN=response.json()['csrf_token'])
        return response

    def case(self):
        response = self.client.post('/investigations', {'finding_id': self.finding.id}, format='json')
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_anonymous_cannot_read_or_write_workspace(self):
        for path in ['/events', '/suspicious', '/stats', '/findings', '/investigations', '/users', '/users/assignable', '/users/access-history']:
            self.assertEqual(self.client.get(path).status_code, 403, path)
        self.assertEqual(self.client.post('/login-attempt', {'ip': '203.0.113.1', 'success': False}, format='json').status_code, 403)
        self.assertEqual(self.client.get('/auth/session').json()['user'], None)

    def test_login_logout_and_writes_require_csrf(self):
        self.assertEqual(self.client.post('/auth/login', {'username': self.admin.username, 'password': PASSWORD}, format='json').status_code, 403)
        token = self.client.get('/auth/session').json()['csrf_token']
        self.assertEqual(self.client.post('/auth/login', {'username': self.admin.username, 'password': PASSWORD}, format='json', HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN='https://untrusted.example').status_code, 403)
        response = self.login()
        self.assertTrue(self.client.cookies['security_dashboard_session']['httponly'])
        self.assertTrue(self.client.cookies['security_dashboard_csrf']['httponly'])
        self.assertNotIn('password', response.json()['user'])
        self.client.credentials()
        self.assertEqual(self.client.post('/investigations', {'finding_id': self.finding.id}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/auth/logout', {}, format='json').status_code, 403)
        self.client.credentials(HTTP_X_CSRFTOKEN=response.json()['csrf_token'])
        self.assertEqual(self.client.post('/auth/logout', {}, format='json').status_code, 200)
        self.assertEqual(self.client.get('/events').status_code, 403)

    def test_viewer_is_read_only_analyst_cannot_ingest_or_manage_accounts(self):
        self.login(self.viewer)
        self.assertEqual(self.client.get('/events').status_code, 200)
        self.assertEqual(self.client.post('/investigations', {'finding_id': self.finding.id}, format='json').status_code, 403)
        self.login(self.analyst)
        case = self.case()
        self.assertEqual(self.client.get('/users').status_code, 403)
        self.assertEqual(self.client.post('/users', {}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/login-attempt', {'ip': '203.0.113.1', 'success': False}, format='json').status_code, 403)
        self.login(self.viewer)
        self.assertEqual(self.client.patch(f"/investigations/{case['id']}", {'revision': 1, 'status': 'investigating'}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f"/investigations/{case['id']}/notes", {'text': 'forbidden'}, format='json').status_code, 403)
        self.assertEqual(InvestigationNote.objects.count(), 0)
        self.assertEqual(AuditEntry.objects.count(), 1)

    def test_authors_are_server_identity_and_forged_fields_rejected(self):
        self.login(self.analyst)
        self.assertEqual(self.client.post('/investigations', {'finding_id': self.finding.id, 'actor': 'forged'}, format='json').status_code, 400)
        case = self.case()
        path = f"/investigations/{case['id']}"
        self.assertEqual(self.client.patch(path, {'revision': 1, 'owner': 'forged'}, format='json').status_code, 400)
        for field in ['actor', 'author', 'author_user']:
            self.assertEqual(self.client.post(path + '/notes', {'text': 'note', field: 'forged'}, format='json').status_code, 400)
        response = self.client.post(path + '/notes', {'text': 'Authenticated reasoning'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['author_user'], self.analyst.id)
        self.assertEqual(response.json()['author'], self.analyst.username)
        self.assertEqual(AuditEntry.objects.last().actor_user_id, self.analyst.id)

    def test_only_active_analysts_or_admins_can_be_assigned(self):
        self.login(self.analyst)
        case = self.case()
        path = f"/investigations/{case['id']}"
        self.assertEqual(self.client.patch(path, {'revision': 1, 'owner_user': self.viewer.id}, format='json').status_code, 400)
        self.admin.is_active = False
        self.admin.save()
        self.assertEqual(self.client.patch(path, {'revision': 1, 'owner_user': self.admin.id}, format='json').status_code, 400)
        assigned = self.client.patch(path, {'revision': 1, 'owner_user': self.analyst.id}, format='json')
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()['owner'], self.analyst.username)
        self.assertEqual([row['id'] for row in self.client.get('/users/assignable').json()], [self.analyst.id])

    def test_admin_provisions_validated_accounts_and_audits_without_passwords(self):
        self.login()
        payload = {'username': 'new-analyst', 'password': 'Provisioned-account-8!Secret', 'role': 'analyst'}
        response = self.client.post('/users', payload, format='json')
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username=payload['username'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.post('/users', payload, format='json').status_code, 400)
        self.assertEqual(self.client.post('/users', {**payload, 'username': 'weak-user', 'password': 'password'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/users', {**payload, 'username': 'extra-user', 'is_superuser': True}, format='json').status_code, 400)
        self.assertEqual(AccessAuditEntry.objects.count(), 1)
        self.assertNotIn('Secret', str(self.client.get('/users/access-history').json()))
        self.assertNotIn('password', str(self.client.get('/users').json()))

    def test_last_admin_is_protected_and_role_changes_apply_to_existing_sessions(self):
        self.login()
        for changes in [{'role': 'viewer'}, {'is_active': False}]:
            self.assertEqual(self.client.patch(f'/users/{self.admin.id}', changes, format='json').status_code, 400)
        other = APIClient(enforce_csrf_checks=True)
        self.login(self.analyst, other)
        self.assertEqual(self.client.patch(f'/users/{self.analyst.id}', {'role': 'viewer'}, format='json').status_code, 200)
        self.assertEqual(other.post('/investigations', {'finding_id': self.finding.id}, format='json').status_code, 403)
        self.assertEqual(other.get('/events').status_code, 200)
        self.assertEqual(self.client.patch(f'/users/{self.analyst.id}', {'is_active': False}, format='json').status_code, 200)
        self.assertEqual(other.get('/events').status_code, 403)
        self.assertEqual(AccessAuditEntry.objects.count(), 2)

    def test_wrong_inactive_and_unknown_passwords_return_same_error(self):
        token = self.client.get('/auth/session').json()['csrf_token']
        self.viewer.is_active = False
        self.viewer.save()
        results = []
        for username, password in [(self.admin.username, 'wrong'), ('missing', PASSWORD), (self.viewer.username, PASSWORD)]:
            response = self.client.post('/auth/login', {'username': username, 'password': password}, format='json', HTTP_X_CSRFTOKEN=token)
            results.append((response.status_code, response.json()))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(results[0][0], 401)

    def test_login_throttle_limits_repeated_attempts(self):
        token = self.client.get('/auth/session').json()['csrf_token']
        # Malformed requests count too, without performing expensive password hashes.
        for _ in range(10):
            self.assertEqual(self.client.post('/auth/login', {}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 400)
        response = self.client.post('/auth/login', {}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
