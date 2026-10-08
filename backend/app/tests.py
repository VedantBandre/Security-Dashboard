from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .detection import BRUTE_FORCE_THRESHOLD, BRUTE_FORCE_WINDOW_MINUTES, is_suspicious
from .models import LoginEvent

# Create your tests here.

# Model Tests
class LoginEventModelTest(TestCase):
    def test_event_creation_defaults(self):
        event = LoginEvent.objects.create(ip_address="10.0.0.1", success=False)
        self.assertEqual(event.ip_address, "10.0.0.1")
        self.assertFalse(event.success)
        self.assertFalse(event.is_suspicious)
        self.assertIsNotNone(event.timestamp)
    
    def test_event_str_respresentation(self):
        event = LoginEvent.objects.create(ip_address="1.2.3.4", success=True)
        self.assertIn('SUCCESS', str(event))
        self.assertIn('1.2.3.4', str(event))
    
    def test_suspicious_flag_str(self):
        event = LoginEvent.objects.create(
            ip_address="1.2.3.4", success=False, is_suspicious=True
        )
        self.assertIn('[SUSPICIOUS]', str(event))


#  Detection Logic Tests
class DetectionLogicTest(TestCase):

    TARGET_IP = "192.168.1.100"
    
    def _make_failed(self, ip=None, minutes_ago=0):
        """Helper to create a failed login event"""
        ip = ip or self.TARGET_IP
        t = timezone.now() - timedelta(minutes=minutes_ago)
        event = LoginEvent(ip_address=ip, success=False, timestamp=t)
        event.save()
        return event
    
    def test_no_suspicion_below_threshold(self):
        for _ in range(BRUTE_FORCE_THRESHOLD):
            self._make_failed()
        self.assertFalse(is_suspicious(self.TARGET_IP))
    
    def test_brute_force_detected_above_thresold(self):
        for _ in range(BRUTE_FORCE_THRESHOLD + 1):
            self._make_failed()
        self.assertTrue(is_suspicious(self.TARGET_IP))
    
    def test_old_events_do_not_trigger_brute_force(self):
        # Events outside the detection window should not be counted
        for _ in range(BRUTE_FORCE_THRESHOLD + 1):
            self._make_failed(minutes_ago=BRUTE_FORCE_WINDOW_MINUTES + 2)
        self.assertFalse(is_suspicious(self.TARGET_IP))
    
    def test_different_ip_not_flagged(self):
        for _ in range(BRUTE_FORCE_THRESHOLD + 1):
            self._make_failed(ip="10.10.10.10")
        # Our target IP has no events - should be clean
        self.assertFalse(is_suspicious(self.TARGET_IP))


# API Endpoints

class LoginAttemptAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user(username='test-admin', is_staff=True))
    
    def test_post_login_attempt_creates_event(self):
        payload = {'ip': '172.16.0.1', 'username': 'alice', 'success': False}
        response = self.client.post('/login-attempt', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LoginEvent.objects.count(), 1)

    def test_post_invalid_ip_returns_400(self):
        payload = {'ip': 'not-an-ip', 'success': False}
        response = self.client.post('/login-attempt', payload, format='json')
        self.assertEqual(response.status_code, 400)
    
    def test_brute_force_marks_suspicious_via_api(self):
        ip = '10.0.0.99'
        # Send enough failures to cross threshold
        for _ in range(BRUTE_FORCE_THRESHOLD + 1):
            self.client.post('/login-attempt', {'ip': ip, 'success': False}, format='json')
        response = self.client.get('/suspicious')
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)
        self.assertTrue(all(e['is_suspicious'] for e in response.data))
    
    def test_get_events_returns_all(self):
        LoginEvent.objects.create(ip_address='1.1.1.1', success=True)
        LoginEvent.objects.create(ip_address='2.2.2.2', success=False)
        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
    
    def test_stats_endpoint(self):
        LoginEvent.objects.create(ip_address='1.1.1.1', success=True)
        LoginEvent.objects.create(ip_address='1.1.1.1', success=False)
        response = self.client.get('/stats')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['failed'], 1)
        self.assertEqual(response.data['succeeded'], 1)