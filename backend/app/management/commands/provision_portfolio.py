"""Initialize a disposable portfolio database once, without resetting records."""
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from app.accounts import set_role
from app.investigations import snapshot
from app.models import (
    AuditEntry,
    DemoDataset,
    DetectionFinding,
    Investigation,
    InvestigationNote,
    LoginEvent,
)
from app.services import ingest_login


class Command(BaseCommand):
    help = 'Provision synthetic portfolio accounts, events, and cases once, only in an empty database.'

    @transaction.atomic
    def handle(self, *args, **options):
        _, created = DemoDataset.objects.get_or_create(key='portfolio-v1')
        if not created:
            self.stdout.write('Portfolio dataset already initialized; existing records and passwords retained.')
            return
        User = get_user_model()
        if User.objects.exists() or LoginEvent.objects.exists() or DetectionFinding.objects.exists():
            raise CommandError('Portfolio provisioning requires an empty database; existing data was not changed.')
        passwords = {}
        for name in ['PORTFOLIO_ADMIN_PASSWORD', 'PORTFOLIO_VIEWER_PASSWORD']:
            password = os.environ.get(name, '')
            try:
                validate_password(password)
            except ValidationError as error:
                raise CommandError(f'{name}: {" ".join(error.messages)}') from error
            passwords[name] = password
        if passwords['PORTFOLIO_ADMIN_PASSWORD'] == passwords['PORTFOLIO_VIEWER_PASSWORD']:
            raise CommandError('Administrator and public Viewer passwords must be different.')
        admin = User.objects.create_user(username='portfolio-admin', password=passwords['PORTFOLIO_ADMIN_PASSWORD'])
        set_role(admin, 'admin')
        viewer = User.objects.create_user(username='portfolio-viewer', password=passwords['PORTFOLIO_VIEWER_PASSWORD'])
        set_role(viewer, 'viewer')
        # Attribution account for synthetic case examples; it cannot sign in.
        analyst = User.objects.create_user(username='demo-analyst', first_name='Demo', last_name='Analyst')
        set_role(analyst, 'analyst')
        now = timezone.now()
        for index in range(48):
            LoginEvent.objects.create(ip_address=f'198.51.100.{10 + index % 6}', username=['demo-alex', 'demo-sam', 'demo-service'][index % 3],
                                      success=index % 8 != 0, timestamp=now - timedelta(minutes=index * 3))
        scenarios = [('203.0.113.50', 6, False), ('203.0.113.77', 11, True), ('203.0.113.91', 6, False)]
        for ip, count, success in scenarios:
            for _ in range(count):
                ingest_login({'ip': ip, 'username': 'synthetic-service', 'success': success})
        for index, finding in enumerate(DetectionFinding.objects.order_by('id')):
            case = Investigation.objects.create(finding=finding, title=f'Demo: {finding.title} — {finding.ip_address}',
                                                severity=finding.severity, owner_user=analyst, owner=analyst.username)
            AuditEntry.objects.create(investigation=case, actor=admin.username, actor_user=admin, action='created', after=snapshot(case))
            if index == 2:
                continue
            before = snapshot(case)
            case.status = 'investigating'
            case.revision += 1
            case.save()
            AuditEntry.objects.create(investigation=case, actor=analyst.username, actor_user=analyst, action='updated', before=before, after=snapshot(case))
            note = InvestigationNote.objects.create(investigation=case, author=analyst.username, author_user=analyst,
                                                    text='Synthetic portfolio example: reviewed the captured events and compared them with the expected demo workload.')
            AuditEntry.objects.create(investigation=case, actor=analyst.username, actor_user=analyst, action='note_added', after={'note_id': note.id})
            if index == 1:
                before = snapshot(case)
                case.status = 'resolved'
                case.disposition = 'benign'
                case.closure_reason = 'Synthetic scheduled service activity; these events were generated for the portfolio walkthrough.'
                case.resolved_at = timezone.now()
                case.revision += 1
                case.save()
                AuditEntry.objects.create(investigation=case, actor=analyst.username, actor_user=analyst, action='resolved', before=before, after=snapshot(case))
        self.stdout.write(self.style.SUCCESS('Portfolio ready: 71 synthetic events, 3 findings, and New / Investigating / Resolved cases. Public account: portfolio-viewer.'))
