from datetime import timedelta
from django.db import transaction
from django.utils import timezone

BRUTE_FORCE_THRESHOLD = 5
BRUTE_FORCE_WINDOW_MINUTES = 5
RATE_THRESHOLD = 10
RATE_WINDOW_SECONDS = 60

RULES = (
    {'id': 'brute_force', 'title': 'Repeated failed logins', 'severity': 'high',
     'threshold': BRUTE_FORCE_THRESHOLD, 'seconds': BRUTE_FORCE_WINDOW_MINUTES * 60, 'failed_only': True},
    {'id': 'rate_abuse', 'title': 'High login attempt rate', 'severity': 'medium',
     'threshold': RATE_THRESHOLD, 'seconds': RATE_WINDOW_SECONDS, 'failed_only': False},
)


def evaluate_rules(ip_address, now=None, rules=RULES):
    """Evaluate rolling windows; future-dated records are excluded."""
    from .models import LoginEvent
    now = now or timezone.now()
    matches = []
    for rule in rules:
        start = now - timedelta(seconds=rule['seconds'])
        events = LoginEvent.objects.filter(ip_address=ip_address, timestamp__gte=start, timestamp__lte=now)
        if rule['failed_only']:
            events = events.filter(success=False)
        if events.count() <= rule['threshold']:
            continue
        evidence = list(events.order_by('timestamp', 'id').values('id', 'ip_address', 'username', 'timestamp', 'success'))
        if len(evidence) > rule['threshold']:
            matches.append((rule, start, now, evidence))
    return matches


def is_suspicious(ip_address):
    return bool(evaluate_rules(ip_address))


@transaction.atomic
def record_findings(ip_address):
    """Freeze evidence once per source/rule cooldown, without extending that cooldown."""
    from .models import DetectionCursor, DetectionFinding
    now = timezone.now()
    findings = []
    # Always lock in the same order, including rules not currently triggered.
    for rule in RULES:
        cursor, _ = DetectionCursor.objects.get_or_create(ip_address=ip_address, rule_id=rule['id'])
        cursor = DetectionCursor.objects.select_for_update().get(pk=cursor.pk)
        matches = [match for match in evaluate_rules(ip_address, now, rules=(rule,)) if match[0]['id'] == rule['id']]
        if not matches:
            continue
        if cursor.finding and cursor.finding.detected_at + timedelta(seconds=rule['seconds']) > now:
            findings.append(cursor.finding)
            continue
        _, start, end, evidence = matches[0]
        for event in evidence:
            event['timestamp'] = event['timestamp'].isoformat()
        finding = DetectionFinding.objects.create(
            ip_address=ip_address, rule_id=rule['id'], title=rule['title'], severity=rule['severity'],
            threshold=rule['threshold'], observed_count=len(evidence), window_seconds=rule['seconds'],
            window_start=start, window_end=end, detected_at=now, evidence=evidence,
        )
        cursor.finding = finding
        cursor.save(update_fields=['finding'])
        findings.append(finding)
    return findings
