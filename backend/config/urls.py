from django.urls import include, path

from .views import health, workspace

urlpatterns = [
    path('', workspace, name='workspace'),
    path('health/', health, name='health'),
    path('', include('app.urls')),
]
