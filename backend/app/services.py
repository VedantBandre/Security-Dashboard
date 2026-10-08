from django.db import transaction
from .models import LoginEvent
from .detection import record_findings


@transaction.atomic
def ingest_login(data):
    event = LoginEvent.objects.create(
        ip_address=data['ip'], username=data.get('username', ''), success=data['success'],
    )
    if record_findings(data['ip']):
        LoginEvent.objects.filter(ip_address=data['ip']).update(is_suspicious=True)
        event.refresh_from_db()
    return event
