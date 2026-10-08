from django.conf import settings
from django.db import models


# Create your models here.
class LoginEvent(models.Model):
    ip_address = models.CharField(max_length=45)
    timestamp = models.DateTimeField(auto_now_add=False, default=None, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            from django.utils import timezone
            self.timestamp = timezone.now()
        super().save(*args, **kwargs)
    
    success = models.BooleanField(default=False)
    username = models.CharField(max_length=150, blank=True, null=True)
    is_suspicious = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        if self.success:
            status = 'SUCCESS'
        else:
            status = 'FAIL'
        
        if self.is_suspicious:
            flag = ' [SUSPICIOUS]'
        else:
            flag = ''
        
        return f"[{self.timestamp}] {self.ip_address} - {status}{flag}"


class DetectionFinding(models.Model):
    ip_address = models.GenericIPAddressField()
    rule_id = models.CharField(max_length=50)
    rule_version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    severity = models.CharField(max_length=10, choices=[('medium', 'Medium'), ('high', 'High')])
    threshold = models.PositiveIntegerField()
    observed_count = models.PositiveIntegerField()
    window_seconds = models.PositiveIntegerField()
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    detected_at = models.DateTimeField()
    evidence = models.JSONField(default=list)

    class Meta:
        ordering = ['-detected_at', '-id']
        indexes = [models.Index(fields=['ip_address', 'rule_id', 'detected_at'])]


class DetectionCursor(models.Model):
    """Serialize each source/rule and retain the finding's cooldown pointer."""
    ip_address = models.GenericIPAddressField()
    rule_id = models.CharField(max_length=50)
    finding = models.ForeignKey(DetectionFinding, null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['ip_address', 'rule_id'], name='unique_source_rule_cursor')]


class Investigation(models.Model):
    STATUSES = [('new', 'New'), ('investigating', 'Investigating'), ('resolved', 'Resolved')]
    SEVERITIES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    DISPOSITIONS = [('true_positive', 'True positive'), ('false_positive', 'False positive'), ('benign', 'Benign')]
    finding = models.OneToOneField(DetectionFinding, on_delete=models.PROTECT, related_name='investigation')
    title = models.CharField(max_length=200)
    severity = models.CharField(max_length=10, choices=SEVERITIES)
    status = models.CharField(max_length=20, choices=STATUSES, default='new')
    owner = models.CharField(max_length=150, blank=True)
    owner_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='assigned_investigations')
    disposition = models.CharField(max_length=20, choices=DISPOSITIONS, blank=True)
    closure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-updated_at', '-id']


class InvestigationNote(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.PROTECT, related_name='notes')
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='investigation_notes')
    author = models.CharField(max_length=150)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class AuditEntry(models.Model):
    investigation = models.ForeignKey(Investigation, on_delete=models.PROTECT, related_name='history')
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='investigation_audit_entries')
    actor = models.CharField(max_length=150)
    action = models.CharField(max_length=30)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class AccessAuditEntry(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='access_changes')
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='access_history')
    action = models.CharField(max_length=30)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
