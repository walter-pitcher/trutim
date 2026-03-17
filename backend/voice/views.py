"""
Voice Control REST API Views.

Provides endpoints for:
- Voice profile management
- Voice command execution (text/keyword-based)
- Model management (list, activate, benchmark)
- Training pipeline control
- Command log and session analytics
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import (
    VoiceProfile, VoiceCommandLog, KeywordSpotterModel,
    TrainingDataset, VoiceSession,
)
from .serializers import (
    VoiceProfileSerializer, VoiceCommandLogSerializer,
    KeywordSpotterModelSerializer, TrainingDatasetSerializer,
    VoiceSessionSerializer, VoiceCommandInputSerializer,
    TrainModelInputSerializer, GenerateDataInputSerializer,
)
from .commands.command_registry import CommandRegistry
from .commands.intent_classifier import IntentClassifier
from .commands.entity_extractor import EntityExtractor
from .engine.keyword_spotter import PLATFORM_KEYWORDS, KEYWORD_LABELS
from .engine.inference_engine import InferenceEngine


class VoiceProfileViewSet(viewsets.ModelViewSet):
    """Manage user voice control profiles."""
    serializer_class = VoiceProfileSerializer

    def get_queryset(self):
        return VoiceProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        profile, created = VoiceProfile.objects.get_or_create(user=request.user)
        return Response(VoiceProfileSerializer(profile).data)

    @action(detail=False, methods=['patch'])
    def update_settings(self, request):
        profile, _ = VoiceProfile.objects.get_or_create(user=request.user)
        serializer = VoiceProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class VoiceCommandView(APIView):
    """Execute voice commands via REST API."""

    def post(self, request):
        """
        Execute a voice command from text or keywords.

        Body:
        {
            "text": "call john",           // recognized text
            "keywords": ["call", "user"],  // spotted keywords
            "room_id": 1                   // optional current room
        }
        """
        serializer = VoiceCommandInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        text = data.get('text', '')
        keywords = data.get('keywords', [])
        room_id = data.get('room_id')

        classifier = IntentClassifier()

        intent = classifier.classify(text=text, keywords=keywords or None)

        VoiceCommandLog.objects.create(
            user=request.user,
            room_id=room_id,
            raw_text=text,
            intent=intent.name,
            confidence=intent.confidence,
            keywords_spotted=keywords,
            success=intent.name != 'unknown',
        )

        return Response({
            'intent': intent.to_dict(),
            'status': 'success' if intent.name != 'unknown' else 'unrecognized',
        })


class VoiceCommandLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View voice command history."""
    serializer_class = VoiceCommandLogSerializer

    def get_queryset(self):
        return VoiceCommandLog.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        logs = VoiceCommandLog.objects.filter(user=request.user)
        total = logs.count()
        successful = logs.filter(success=True).count()
        avg_confidence = 0
        if total > 0:
            from django.db.models import Avg
            avg_confidence = logs.aggregate(Avg('confidence'))['confidence__avg'] or 0

        return Response({
            'total_commands': total,
            'successful_commands': successful,
            'success_rate': successful / max(total, 1),
            'avg_confidence': avg_confidence,
        })


class KeywordSpotterModelViewSet(viewsets.ModelViewSet):
    """Manage keyword spotting models."""
    serializer_class = KeywordSpotterModelSerializer
    queryset = KeywordSpotterModel.objects.all()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Set a model as the active keyword spotter."""
        model_obj = self.get_object()
        KeywordSpotterModel.objects.filter(is_active=True).update(is_active=False)
        model_obj.is_active = True
        model_obj.save()
        return Response({
            'status': 'activated',
            'model': KeywordSpotterModelSerializer(model_obj).data,
        })

    @action(detail=True, methods=['get'])
    def benchmark(self, request, pk=None):
        """Benchmark model inference performance."""
        model_obj = self.get_object()
        engine = InferenceEngine()

        if engine.load_tflite_model(model_obj.name, model_obj.tflite_path or None):
            results = engine.benchmark(model_obj.name)
        elif engine.load_tf_model(model_obj.name, model_obj.model_path or None):
            results = engine.benchmark(model_obj.name)
        else:
            return Response(
                {'error': 'Could not load model for benchmarking'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(results)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the currently active model."""
        model = KeywordSpotterModel.objects.filter(is_active=True).first()
        if model:
            return Response(KeywordSpotterModelSerializer(model).data)
        return Response({'error': 'No active model'}, status=status.HTTP_404_NOT_FOUND)


class TrainingDatasetViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingDatasetSerializer
    queryset = TrainingDataset.objects.all()


class VoiceSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VoiceSessionSerializer

    def get_queryset(self):
        return VoiceSession.objects.filter(user=self.request.user)


class VoiceSystemInfoView(APIView):
    """System information and available commands."""

    def get(self, request):
        """Get voice control system information."""
        CommandRegistry.auto_discover()

        active_model = KeywordSpotterModel.objects.filter(is_active=True).first()

        return Response({
            'system': {
                'name': 'Trutim Voice Control',
                'version': '1.0.0',
                'wake_word': 'trutim',
                'status': 'active',
            },
            'keywords': {
                'vocabulary': PLATFORM_KEYWORDS,
                'labels': KEYWORD_LABELS,
                'total': len(PLATFORM_KEYWORDS),
            },
            'commands': CommandRegistry.serialize_commands(),
            'active_model': (
                KeywordSpotterModelSerializer(active_model).data
                if active_model else None
            ),
            'architectures': [
                {'name': 'ds_cnn', 'label': 'DS-CNN (Lightweight)', 'params': '~80K'},
                {'name': 'attention_rnn', 'label': 'Attention RNN', 'params': '~250K'},
                {'name': 'tc_resnet', 'label': 'TC-ResNet (Streaming)', 'params': '~150K'},
                {'name': 'conformer', 'label': 'Conformer (Best Accuracy)', 'params': '~500K'},
                {'name': 'multi_head', 'label': 'Multi-Head Spotter', 'params': '~350K'},
            ],
        })


class TrainModelView(APIView):
    """Trigger model training."""

    def post(self, request):
        serializer = TrainModelInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        return Response({
            'status': 'training_queued',
            'config': data,
            'message': (
                f"Training {data['architecture']} model queued. "
                f"Use management command 'python manage.py train_wake_word "
                f"--architecture {data['architecture']}' to start training."
            ),
        })


class GenerateDataView(APIView):
    """Trigger training data generation."""

    def post(self, request):
        serializer = GenerateDataInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        return Response({
            'status': 'generation_queued',
            'config': data,
            'message': (
                "Data generation queued. Use management command "
                "'python manage.py generate_training_data' to start."
            ),
        })
