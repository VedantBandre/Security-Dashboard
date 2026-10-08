from rest_framework import serializers

from .models import LoginEvent


class LoginEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginEvent
        fields = ['id', 'ip_address', 'timestamp', 'success', 'username', 'is_suspicious']
        read_only_fields = ['id', 'timestamp', 'is_suspicious']

class LoginAttemptInputSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    username = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')        
    success = serializers.BooleanField()