from ipaddress import ip_address

from django.core.management.base import BaseCommand, CommandError

from app.models import DetectionFinding
from app.services import ingest_login


class Command(BaseCommand):
    help = 'Append synthetic login activity for a local investigation demo. Existing records are retained.'

    def add_arguments(self, parser):
        parser.add_argument('--scenario', choices=['normal', 'brute-force', 'rate-abuse'], default='brute-force')
        parser.add_argument('--ip', default='203.0.113.50')

    def handle(self, *args, **options):
        try:
            source = str(ip_address(options['ip']))
        except ValueError as error:
            raise CommandError('Provide a valid IP address.') from error
        scenario = options['scenario']
        count = {'normal': 3, 'brute-force': 6, 'rate-abuse': 11}[scenario]
        before = DetectionFinding.objects.count()
        for _ in range(count):
            ingest_login({'ip': source, 'username': f'demo-{scenario}', 'success': scenario != 'brute-force'})
        self.stdout.write(self.style.SUCCESS(f'Appended {count} demo events for {source}; created {DetectionFinding.objects.count() - before} findings.'))
