from django.urls import path
from .views import LoginAttemptView, EventListView, SuspiciousEventsView, StatsView

urlpatterns = [
    path('login-attempt', LoginAttemptView.as_view(), name='login-attempt'),
    path('events', EventListView.as_view(), name='events'),
    path('suspicious', SuspiciousEventsView.as_view(), name='suspicious'),
    path('stats', StatsView.as_view(), name='stats'),
]
from .investigations import FindingsView, FindingView, InvestigationsView, InvestigationView, NotesView

urlpatterns += [
    path('findings', FindingsView.as_view(), name='findings'),
    path('findings/<int:pk>', FindingView.as_view(), name='finding'),
    path('investigations', InvestigationsView.as_view(), name='investigations'),
    path('investigations/<int:pk>', InvestigationView.as_view(), name='investigation'),
    path('investigations/<int:pk>/notes', NotesView.as_view(), name='investigation-notes'),
]
