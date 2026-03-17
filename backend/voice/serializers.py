"""
Voice Control Serializers for Django REST Framework.
"""
from rest_framework import serializers
from .models import (
    VoiceProfile, VoiceCommandLog, KeywordSpotterModel,
    TrainingDataset, VoiceSession,
)


class VoiceProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = VoiceProfile
        fields = [
            'id', 'username', 'enabled', 'wake_word', 'confidence_threshold',
            'noise_reduction_level', 'language', 'use_vad',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'username', 'created_at', 'updated_at']


class VoiceCommandLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = VoiceCommandLog
        fields = [
            'id', 'username', 'room', 'raw_text', 'intent', 'confidence',
            'entities', 'command_result', 'success', 'latency_ms',
            'keywords_spotted', 'wake_word_confidence', 'created_at',
        ]
        read_only_fields = ['id', 'username', 'created_at']


class KeywordSpotterModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordSpotterModel
        fields = [
            'id', 'name', 'architecture', 'version', 'model_path',
            'tflite_path', 'num_parameters', 'num_keywords', 'accuracy',
            'training_epochs', 'training_samples', 'is_active',
            'metadata', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TrainingDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingDataset
        fields = [
            'id', 'name', 'data_dir', 'num_samples', 'num_keywords',
            'sample_rate', 'duration_per_sample_s', 'manifest', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class VoiceSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = VoiceSession
        fields = [
            'id', 'username', 'room', 'started_at', 'ended_at',
            'total_commands', 'successful_commands',
            'total_audio_duration_s', 'wake_word_detections',
        ]
        read_only_fields = ['id', 'username', 'started_at']


class VoiceCommandInputSerializer(serializers.Serializer):
    """Serializer for voice command execution via REST API."""
    text = serializers.CharField(required=False, allow_blank=True)
    keywords = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    room_id = serializers.IntegerField(required=False, allow_null=True)


class TrainModelInputSerializer(serializers.Serializer):
    """Serializer for training initiation."""
    architecture = serializers.ChoiceField(
        choices=['ds_cnn', 'attention_rnn', 'tc_resnet', 'conformer', 'multi_head'],
        default='ds_cnn',
    )
    epochs = serializers.IntegerField(default=100, min_value=1, max_value=1000)
    batch_size = serializers.IntegerField(default=64, min_value=8, max_value=512)
    learning_rate = serializers.FloatField(default=0.001, min_value=1e-7, max_value=1.0)


class GenerateDataInputSerializer(serializers.Serializer):
    """Serializer for training data generation."""
    samples_per_keyword = serializers.IntegerField(default=2000, min_value=10)
    num_speakers = serializers.IntegerField(default=50, min_value=1)
    keywords = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
