# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import LoginEvent
from .serializers import LoginEventSerializer, LoginAttemptInputSerializer
from .services import ingest_login
from .permissions import AdminPermission
from rest_framework.permissions import IsAuthenticated

# Create your views here.
class LoginAttemptView(APIView):
    """
    POST /login-attempt
    Record a login attempt and run detection logic.
    """
    permission_classes = [IsAuthenticated, AdminPermission]
    def post(self, request):
        serializer = LoginAttemptInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        event = ingest_login(serializer.validated_data)

        return Response(LoginEventSerializer(event).data, status=status.HTTP_201_CREATED)


class EventListView(APIView):
    """GET /events - all events, newest first"""

    def get(self, request):
        events = LoginEvent.objects.all()
        return Response(LoginEventSerializer(events, many=True).data)


class SuspiciousEventsView(APIView):
    """GET /suspicious - only flagged events"""
    
    def get(self, request):
        events = LoginEvent.objects.filter(is_suspicious=True)
        return Response(LoginEventSerializer(events, many=True).data)


class StatsView(APIView):
    """GET /stats - aggregate counts for the dashboard"""

    def get(self, request):
        total = LoginEvent.objects.count()
        failed = LoginEvent.objects.filter(success=False).count()
        succeeded = LoginEvent.objects.filter(success=True).count()
        suspicious = LoginEvent.objects.filter(is_suspicious=True).count()
        
        return Response({
            'total': total,
            'failed': failed,
            'succeeded': succeeded,
            'suspicious': suspicious,
        })