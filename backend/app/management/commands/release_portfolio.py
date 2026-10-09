from config.environment import boolean
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Serialize PostgreSQL release setup, then optionally provision an empty portfolio database.'

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Portfolio release setup requires PostgreSQL.')
        # Session lock covers migrations too, before the demo marker table exists.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_lock(%s)', [47281932])
        try:
            call_command('migrate', interactive=False)
            call_command('createcachetable')
            if boolean('PORTFOLIO_PROVISION'):
                call_command('provision_portfolio')
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [47281932])
