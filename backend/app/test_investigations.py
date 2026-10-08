from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from .models import LoginEvent, DetectionFinding, Investigation, AuditEntry
from .detection import is_suspicious


class InvestigationWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='analyst-a', is_staff=True)
        self.other = get_user_model().objects.create_user(username='analyst-b', is_staff=True)
        self.client.force_authenticate(self.user)
        self.ip = '203.0.113.10'

    def ingest(self, count=6, success=False):
        for _ in range(count):
            response = self.client.post('/login-attempt', {'ip': self.ip, 'username': 'demo', 'success': success}, format='json')
            self.assertEqual(response.status_code, 201)
        return DetectionFinding.objects.first()

    def create_case(self):
        finding = self.ingest()
        response = self.client.post('/investigations', {'finding_id': finding.id}, format='json')
        self.assertEqual(response.status_code, 201)
        return finding, response.data

    def update(self, case, **changes):
        return self.client.patch(f"/investigations/{case['id']}", {'revision': case['revision'], **changes}, format='json')

    def test_finding_freezes_evidence_and_deduplicates_burst(self):
        finding = self.ingest()
        snapshot = finding.evidence
        self.ingest(3)
        self.assertEqual(DetectionFinding.objects.count(), 1)
        finding.refresh_from_db()
        self.assertEqual(finding.observed_count, 6)
        self.assertEqual(finding.evidence, snapshot)
        self.assertEqual(len(snapshot), 6)
        self.assertEqual(finding.severity, 'high')
        self.assertTrue(all(not event['success'] for event in snapshot))

    def test_rate_rule_has_its_own_threshold_and_severity(self):
        finding = self.ingest(11, success=True)
        self.assertEqual(finding.rule_id, 'rate_abuse')
        self.assertEqual(finding.severity, 'medium')
        self.assertEqual(finding.observed_count, 11)
        self.assertEqual(finding.threshold, 10)
        self.ingest(1, success=True)
        self.assertEqual(DetectionFinding.objects.count(), 1)

    def test_new_finding_after_cooldown_retains_old_snapshot(self):
        now = timezone.now()
        with patch('app.detection.timezone.now', return_value=now):
            first = self.ingest()
        with patch('app.detection.timezone.now', return_value=now + timedelta(seconds=301)):
            second = self.ingest()
        self.assertNotEqual(first.id, second.id)
        first.refresh_from_db()
        self.assertEqual(first.observed_count, 6)
        self.assertEqual(second.observed_count, 6)

    def test_future_events_are_not_detection_evidence(self):
        for _ in range(6):
            LoginEvent.objects.create(ip_address=self.ip, timestamp=timezone.now() + timedelta(hours=1), success=False)
        self.assertFalse(is_suspicious(self.ip))

    def test_case_creation_is_idempotent_per_finding(self):
        finding, case = self.create_case()
        again = self.client.post('/investigations', {'finding_id': finding.id}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(case['id'], again.data['id'])
        self.assertEqual(Investigation.objects.count(), 1)
        self.assertEqual(AuditEntry.objects.count(), 1)

    def test_full_workflow_persists_evidence_notes_resolution_and_reopen_history(self):
        finding, case = self.create_case()
        case = self.update(case, status='investigating', owner_user=self.user.id).data
        note = self.client.post(f"/investigations/{case['id']}/notes", {'text': 'Reviewed six failures from the same source.'}, format='json')
        self.assertEqual(note.status_code, 201)
        closed = self.update(case, status='resolved', disposition='true_positive', closure_reason='Repeated failures confirmed by captured evidence.')
        self.assertEqual(closed.status_code, 200)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        persisted = self.client.get(f"/investigations/{case['id']}").data
        self.assertEqual(persisted['status'], 'resolved')
        self.assertEqual(persisted['disposition'], 'true_positive')
        self.assertEqual(len(persisted['notes']), 1)
        self.assertEqual(persisted['finding']['evidence'], finding.evidence)
        self.assertEqual([row['action'] for row in persisted['history']], ['created', 'updated', 'note_added', 'resolved'])
        reopened = self.update(persisted, status='investigating')
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.data['disposition'], '')
        self.assertIsNone(reopened.data['resolved_at'])
        self.assertEqual(reopened.data['history'][-1]['before']['disposition'], 'true_positive')
        self.assertEqual(reopened.data['history'][-1]['action'], 'reopened')
        self.assertEqual(LoginEvent.objects.count(), 6)

    def test_resolution_requires_investigating_and_a_reason(self):
        _, case = self.create_case()
        self.assertEqual(self.update(case, status='resolved', disposition='benign', closure_reason='Test').status_code, 400)
        case = self.update(case, status='investigating').data
        for changes in [dict(status='resolved'), dict(status='resolved', disposition='benign'), dict(status='resolved', disposition='benign', closure_reason='  ')]:
            self.assertEqual(self.update(case, **changes).status_code, 400)
        self.assertEqual(Investigation.objects.get(pk=case['id']).status, 'investigating')
        self.assertEqual(AuditEntry.objects.count(), 2)

    def test_stale_revision_cannot_overwrite_assignment(self):
        _, old = self.create_case()
        updated = self.update(old, owner_user=self.other.id)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.update(old, owner_user=None).status_code, 409)
        self.assertEqual(Investigation.objects.get(pk=old['id']).owner, 'analyst-b')
        self.assertEqual(AuditEntry.objects.count(), 2)

    def test_resolved_decision_cannot_be_rewritten_without_reopening(self):
        _, case = self.create_case()
        case = self.update(case, status='investigating').data
        case = self.update(case, status='resolved', disposition='benign', closure_reason='Known demo traffic.').data
        self.assertEqual(self.update(case, closure_reason='Changed').status_code, 400)

    def test_validated_queue_filters_and_missing_records(self):
        _, case = self.create_case()
        self.assertEqual(len(self.client.get('/investigations', {'status': 'new', 'source': self.ip}).data), 1)
        self.assertEqual(self.client.get('/investigations', {'status': 'unknown'}).status_code, 400)
        self.assertEqual(self.client.get('/findings', {'source': 'bad-ip'}).status_code, 400)
        self.assertEqual(self.client.get('/investigations/9999').status_code, 404)
        self.assertEqual(self.client.post(f"/investigations/{case['id']}/notes", {'actor': ' ', 'text': 'note'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(f"/investigations/{case['id']}/notes", {'actor': 'A', 'text': ' '}, format='json').status_code, 400)

    def test_legacy_flags_do_not_invent_detection_findings(self):
        LoginEvent.objects.create(ip_address=self.ip, success=False, is_suspicious=True)
        self.assertEqual(self.client.get('/findings').data, [])
