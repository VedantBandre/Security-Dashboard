from app.permissions import role_for
from django.conf import settings
from django.contrib.auth import logout


class ValidateHostMiddleware:
    """Validate even public/static requests before a middleware can short-circuit."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.get_host()
        return self.get_response(request)


class PortfolioGuestMiddleware:
    """Revoke public sessions if demo access is disabled or the account gains privileges."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get('portfolio_guest'):
            if not settings.PORTFOLIO_MODE or request.user.get_username() != 'portfolio-viewer' or role_for(request.user) != 'viewer':
                logout(request)
        return self.get_response(request)
