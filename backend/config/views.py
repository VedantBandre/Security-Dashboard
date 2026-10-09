"""Public entry document and minimal operational readiness endpoint."""
from django.conf import settings
from django.db import DatabaseError, connection
from django.http import FileResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


@never_cache
@require_GET
def workspace(request):
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.is_file():
        return JsonResponse({'detail': 'Frontend build unavailable.'}, status=503)
    return FileResponse(index.open('rb'), content_type='text/html')
