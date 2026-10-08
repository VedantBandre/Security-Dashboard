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


from .accounts import session_view, login_view, logout_view, AssignableUsersView, UsersView, UserView, AccessHistoryView
urlpatterns += [
    path('auth/session', session_view, name='auth-session'),
    path('auth/login', login_view, name='auth-login'),
    path('auth/logout', logout_view, name='auth-logout'),
    path('users/assignable', AssignableUsersView.as_view(), name='assignable-users'),
    path('users/access-history', AccessHistoryView.as_view(), name='access-history'),
    path('users', UsersView.as_view(), name='users'),
    path('users/<int:pk>', UserView.as_view(), name='user'),
]
