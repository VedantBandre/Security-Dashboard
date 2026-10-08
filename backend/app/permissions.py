from rest_framework.permissions import SAFE_METHODS, BasePermission


def role_for(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_staff or user.is_superuser:
        return 'admin'
    if user.groups.filter(name='Analysts').exists():
        return 'analyst'
    if user.groups.filter(name='Viewers').exists():
        return 'viewer'
    return None


class WorkspacePermission(BasePermission):
    def has_permission(self, request, view):
        role = role_for(request.user)
        return role in {'admin', 'analyst', 'viewer'} and (request.method in SAFE_METHODS or role in {'admin', 'analyst'})


class AdminPermission(BasePermission):
    def has_permission(self, request, view):
        return role_for(request.user) == 'admin'


def exception_handler(exc, context):
    from rest_framework.views import exception_handler as default_handler
    response = default_handler(exc, context)
    if response is not None and isinstance(response.data, dict):
        codes = exc.get_codes() if hasattr(exc, 'get_codes') else None
        if isinstance(codes, str):
            response.data['code'] = codes
    return response
