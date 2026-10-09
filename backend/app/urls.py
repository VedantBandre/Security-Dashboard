from django.urls import path

from .accounts import (
    AccessHistoryView,
    AssignableUsersView,
    UsersView,
    UserView,
    demo_login_view,
    login_view,
    logout_view,
    session_view,
)
from .investigations import (
    FindingsView,
    FindingView,
    InvestigationsView,
    InvestigationView,
    NotesView,
)
from .views import EventListView, LoginAttemptView, StatsView, SuspiciousEventsView

urlpatterns = [
    path('login-attempt', LoginAttemptView.as_view(), name='login-attempt'),
    path('events', EventListView.as_view(), name='events'),
    path('suspicious', SuspiciousEventsView.as_view(), name='suspicious'),
    path('stats', StatsView.as_view(), name='stats'),
]

urlpatterns += [
    path('findings', FindingsView.as_view(), name='findings'),
    path('findings/<int:pk>', FindingView.as_view(), name='finding'),
    path('investigations', InvestigationsView.as_view(), name='investigations'),
    path('investigations/<int:pk>', InvestigationView.as_view(), name='investigation'),
    path('investigations/<int:pk>/notes', NotesView.as_view(), name='investigation-notes'),
]

urlpatterns += [
    path('auth/session', session_view, name='auth-session'),
    path('auth/demo-login', demo_login_view, name='auth-demo-login'),
    path('auth/login', login_view, name='auth-login'),
    path('auth/logout', logout_view, name='auth-logout'),
    path('users/assignable', AssignableUsersView.as_view(), name='assignable-users'),
    path('users/access-history', AccessHistoryView.as_view(), name='access-history'),
    path('users', UsersView.as_view(), name='users'),
    path('users/<int:pk>', UserView.as_view(), name='user'),
]
