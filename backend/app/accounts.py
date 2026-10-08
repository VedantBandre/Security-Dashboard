import json
from math import ceil
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework.validators import UniqueValidator
from .models import AccessAuditEntry
from .permissions import AdminPermission, role_for

User = get_user_model()


def user_data(user):
    return {'id': user.id, 'username': user.get_username(), 'display_name': user.get_full_name() or user.get_username(),
            'role': role_for(user), 'is_active': user.is_active}


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({field: 'This field is not accepted.' for field in unknown})
        return super().to_internal_value(data)


class LoginThrottle(SimpleRateThrottle):
    scope = 'workspace_login'
    rate = '10/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.META.get('REMOTE_ADDR', '')}


def csrf_failure(request, reason=''):
    return JsonResponse({'detail': 'Security check failed. Reload the page and try again.', 'code': 'csrf_failed'}, status=403)


@never_cache
@require_GET
def session_view(request):
    user = request.user
    return JsonResponse({'user': user_data(user) if user.is_authenticated and user.is_active else None, 'csrf_token': get_token(request)})


@never_cache
@require_POST
@csrf_protect
def login_view(request):
    throttle = LoginThrottle()
    if not throttle.allow_request(request, None):
        response = JsonResponse({'detail': 'Too many sign-in attempts. Try again shortly.'}, status=429)
        response['Retry-After'] = str(ceil(throttle.wait()))
        return response
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Provide a username and password.'}, status=400)
    if not isinstance(data, dict) or not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
        return JsonResponse({'detail': 'Provide a username and password.'}, status=400)
    if len(data['username']) > 150 or len(data['password']) > 1024:
        return JsonResponse({'detail': 'Unable to sign in with those credentials.'}, status=400)
    user = authenticate(request, username=data['username'], password=data['password'])
    if not user:
        return JsonResponse({'detail': 'Unable to sign in with those credentials.'}, status=401)
    if not role_for(user):
        return JsonResponse({'detail': 'This account has no workspace role. Contact an administrator.'}, status=403)
    login(request, user)
    return JsonResponse({'user': user_data(user), 'csrf_token': get_token(request)})


@never_cache
@require_POST
@csrf_protect
def logout_view(request):
    logout(request)
    return JsonResponse({'user': None, 'csrf_token': get_token(request)})


def set_role(user, role):
    user.is_staff = role == 'admin'
    # Portal administrators do not need Django's unrestricted superuser flag.
    user.is_superuser = False
    user.save(update_fields=['is_staff', 'is_superuser'])
    user.groups.remove(*Group.objects.filter(name__in=['Analysts', 'Viewers']))
    if role != 'admin':
        user.groups.add(Group.objects.get_or_create(name='Analysts' if role == 'analyst' else 'Viewers')[0])


def access_snapshot(user):
    return {'username': user.get_username(), 'role': role_for(user) if user.is_active else
            ('admin' if user.is_staff or user.is_superuser else 'analyst' if user.groups.filter(name='Analysts').exists() else 'viewer' if user.groups.filter(name='Viewers').exists() else None),
            'is_active': user.is_active}


class CreateUserInput(StrictInput):
    username = serializers.CharField(max_length=150, validators=[User._meta.get_field('username').validators[0], UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(min_length=8, max_length=1024, write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=['viewer', 'analyst', 'admin'])

    def validate(self, data):
        try:
            validate_password(data['password'], User(username=data['username']))
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': error.messages})
        return data


class ChangeUserInput(StrictInput):
    role = serializers.ChoiceField(choices=['viewer', 'analyst', 'admin'], required=False)
    is_active = serializers.BooleanField(required=False)

    def validate(self, data):
        if not data:
            raise serializers.ValidationError('Provide a role or activation change.')
        return data


class AssignableUsersView(APIView):
    def get(self, request):
        users = User.objects.filter(is_active=True).filter(Q(is_staff=True) | Q(is_superuser=True) | Q(groups__name='Analysts')).distinct().order_by('username')
        return Response([user_data(user) for user in users])


class UsersView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        return Response([{**user_data(user), 'role': access_snapshot(user)['role']} for user in User.objects.order_by('username')])

    @transaction.atomic
    def post(self, request):
        serializer = CreateUserInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create_user(username=data['username'], password=data['password'])
        set_role(user, data['role'])
        AccessAuditEntry.objects.create(actor=request.user, target=user, action='created', after=access_snapshot(user))
        return Response(user_data(user), status=201)


class UserView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    @transaction.atomic
    def patch(self, request, pk):
        serializer = ChangeUserInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Lock the administrator set in a fixed order to protect the last-admin invariant.
        list(User.objects.select_for_update().filter(Q(is_staff=True) | Q(is_superuser=True) | Q(pk=pk)).order_by('id'))
        request.user.refresh_from_db()
        if role_for(request.user) != 'admin':
            return Response({'detail': 'Administrator access is required.'}, status=403)
        user = get_object_or_404(User, pk=pk)
        before = access_snapshot(user)
        data = serializer.validated_data
        next_role = data.get('role', before['role'])
        next_active = data.get('is_active', user.is_active)
        if before['role'] == 'admin' and user.is_active and (next_role != 'admin' or not next_active):
            other_admin = User.objects.filter(is_active=True).filter(Q(is_staff=True) | Q(is_superuser=True)).exclude(pk=pk).exists()
            if not other_admin:
                raise serializers.ValidationError({'detail': 'Keep at least one active administrator.'})
        if 'role' in data:
            set_role(user, next_role)
        if 'is_active' in data:
            user.is_active = next_active
            user.save(update_fields=['is_active'])
        AccessAuditEntry.objects.create(actor=request.user, target=user, action='access_changed', before=before, after=access_snapshot(user))
        return Response({**user_data(user), 'role': access_snapshot(user)['role']})


class AccessHistoryView(APIView):
    permission_classes = [IsAuthenticated, AdminPermission]

    def get(self, request):
        entries = AccessAuditEntry.objects.select_related('actor', 'target').all()[:100]
        return Response([{'id': entry.id, 'actor': entry.actor.get_username(), 'target': entry.target.get_username(),
                          'action': entry.action, 'before': entry.before, 'after': entry.after, 'created_at': entry.created_at}
                         for entry in entries])
