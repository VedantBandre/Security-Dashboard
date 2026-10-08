from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .accounts import StrictInput
from .models import AuditEntry, DetectionFinding, Investigation, InvestigationNote
from .permissions import role_for


class FindingSummarySerializer(serializers.ModelSerializer):
    investigation_id = serializers.IntegerField(source='investigation.id', read_only=True, default=None)

    class Meta:
        model = DetectionFinding
        fields = ['id', 'ip_address', 'rule_id', 'rule_version', 'title', 'severity', 'threshold',
                  'observed_count', 'window_seconds', 'window_start', 'window_end', 'detected_at', 'investigation_id']


class FindingDetailSerializer(FindingSummarySerializer):
    class Meta(FindingSummarySerializer.Meta):
        fields = FindingSummarySerializer.Meta.fields + ['evidence']


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationNote
        fields = ['id', 'author', 'author_user', 'text', 'created_at']


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = ['id', 'actor', 'actor_user', 'action', 'before', 'after', 'created_at']


class InvestigationSummarySerializer(serializers.ModelSerializer):
    finding = FindingSummarySerializer(read_only=True)

    class Meta:
        model = Investigation
        fields = ['id', 'title', 'severity', 'status', 'owner', 'disposition', 'closure_reason',
                  'created_at', 'updated_at', 'resolved_at', 'revision', 'finding', 'owner_user']


class InvestigationDetailSerializer(InvestigationSummarySerializer):
    finding = FindingDetailSerializer(read_only=True)
    notes = NoteSerializer(many=True, read_only=True)
    history = AuditSerializer(many=True, read_only=True)

    class Meta(InvestigationSummarySerializer.Meta):
        fields = InvestigationSummarySerializer.Meta.fields + ['notes', 'history']


class OwnerInput(StrictInput):
    def validate_owner_user(self, user):
        if user and role_for(user) not in {'admin', 'analyst'}:
            raise serializers.ValidationError('Assign an active analyst or administrator.')
        return user


class CreateInput(OwnerInput):
    finding_id = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    owner_user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(is_active=True), required=False, allow_null=True, default=None)


class UpdateInput(OwnerInput):
    revision = serializers.IntegerField(min_value=1)
    title = serializers.CharField(max_length=200, required=False)
    owner_user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(is_active=True), required=False, allow_null=True)
    severity = serializers.ChoiceField(choices=Investigation.SEVERITIES, required=False)
    status = serializers.ChoiceField(choices=Investigation.STATUSES, required=False)
    disposition = serializers.ChoiceField(choices=Investigation.DISPOSITIONS, required=False)
    closure_reason = serializers.CharField(max_length=2000, required=False)


class NoteInput(StrictInput):
    text = serializers.CharField(max_length=5000)


class QueueFilters(StrictInput):
    status = serializers.ChoiceField(choices=Investigation.STATUSES, required=False)
    severity = serializers.ChoiceField(choices=Investigation.SEVERITIES, required=False)
    source = serializers.IPAddressField(required=False)
    owner = serializers.CharField(max_length=150, required=False, allow_blank=True)


def snapshot(case):
    return {field: getattr(case, field) for field in
            ['title', 'severity', 'status', 'owner', 'owner_user_id', 'disposition', 'closure_reason', 'revision']}


def detail(case):
    return InvestigationDetailSerializer(case).data


class FindingsView(APIView):
    def get(self, request):
        findings = DetectionFinding.objects.select_related('investigation').all()
        if 'source' in request.query_params:
            filters = QueueFilters(data={'source': request.query_params['source']})
            filters.is_valid(raise_exception=True)
            findings = findings.filter(ip_address=filters.validated_data['source'])
        return Response(FindingSummarySerializer(findings, many=True).data)


class FindingView(APIView):
    def get(self, request, pk):
        finding = get_object_or_404(DetectionFinding.objects.select_related('investigation'), pk=pk)
        return Response(FindingDetailSerializer(finding).data)


class InvestigationsView(APIView):
    def get(self, request):
        filters = QueueFilters(data=request.query_params)
        filters.is_valid(raise_exception=True)
        cases = Investigation.objects.select_related('finding').all()
        for field, value in filters.validated_data.items():
            cases = cases.filter(**{('finding__ip_address' if field == 'source' else field): value})
        return Response(InvestigationSummarySerializer(cases, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = CreateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        finding = get_object_or_404(DetectionFinding.objects.select_for_update(), pk=data['finding_id'])
        case, created = Investigation.objects.get_or_create(finding=finding, defaults={
            'title': data.get('title', f"{finding.title} — {finding.ip_address}"),
            'severity': finding.severity, 'owner_user': data['owner_user'],
            'owner': data['owner_user'].get_username() if data['owner_user'] else '',
        })
        if created:
            AuditEntry.objects.create(investigation=case, actor=request.user.get_username(), actor_user=request.user, action='created', after=snapshot(case))
        return Response(detail(case), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class InvestigationView(APIView):
    def get(self, request, pk):
        case = get_object_or_404(Investigation.objects.select_related('finding').prefetch_related('notes', 'history'), pk=pk)
        return Response(detail(case))

    @transaction.atomic
    def patch(self, request, pk):
        serializer = UpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        case = get_object_or_404(Investigation.objects.select_for_update().select_related('finding'), pk=pk)
        if data['revision'] != case.revision:
            return Response({'detail': 'This investigation changed. Reload it before saving.'}, status=409)
        next_status = data.get('status', case.status)
        allowed = {'new': {'new', 'investigating'}, 'investigating': {'investigating', 'resolved'}, 'resolved': {'resolved', 'investigating'}}
        if next_status not in allowed[case.status]:
            raise serializers.ValidationError({'status': 'Start investigating before resolving a case.'})
        if case.status == 'resolved' and next_status == 'resolved' and any(key in data for key in ['disposition', 'closure_reason']):
            raise serializers.ValidationError({'status': 'Reopen the investigation before changing its resolution.'})
        if next_status == 'resolved' and case.status != 'resolved':
            if not data.get('disposition') or not data.get('closure_reason'):
                raise serializers.ValidationError({'resolution': 'A disposition and closure reason are required.'})
        elif any(key in data for key in ['disposition', 'closure_reason']):
            raise serializers.ValidationError({'resolution': 'Resolution fields are only accepted when resolving.'})
        before = snapshot(case)
        updates = {key: value for key, value in data.items() if key != 'revision'}
        if not updates:
            raise serializers.ValidationError({'detail': 'Provide at least one change.'})
        if next_status == 'resolved' and case.status != 'resolved':
            updates['resolved_at'] = timezone.now()
        elif case.status == 'resolved' and next_status == 'investigating':
            updates.update(resolved_at=None, disposition='', closure_reason='')
        if 'owner_user' in updates:
            updates['owner'] = updates['owner_user'].get_username() if updates['owner_user'] else ''
        updates.update(updated_at=timezone.now(), revision=F('revision') + 1)
        changed = Investigation.objects.filter(pk=case.pk, revision=data['revision']).update(**updates)
        if not changed:
            return Response({'detail': 'This investigation changed. Reload it before saving.'}, status=409)
        case.refresh_from_db()
        action = 'resolved' if next_status == 'resolved' and before['status'] != next_status else 'reopened' if before['status'] == 'resolved' and next_status != 'resolved' else 'updated'
        AuditEntry.objects.create(investigation=case, actor=request.user.get_username(), actor_user=request.user, action=action, before=before, after=snapshot(case))
        return Response(detail(case))


class NotesView(APIView):
    @transaction.atomic
    def post(self, request, pk):
        serializer = NoteInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = get_object_or_404(Investigation.objects.select_for_update(), pk=pk)
        data = serializer.validated_data
        note = InvestigationNote.objects.create(investigation=case, author=request.user.get_username(), author_user=request.user, text=data['text'])
        AuditEntry.objects.create(investigation=case, actor=request.user.get_username(), actor_user=request.user, action='note_added', after={'note_id': note.id})
        return Response(NoteSerializer(note).data, status=201)
