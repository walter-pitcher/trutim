"""
Voice Control Admin registration.
"""
from django.contrib import admin
from .models import (
    VoiceProfile, VoiceCommandLog, KeywordSpotterModel,
    TrainingDataset, VoiceSession,
)


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'enabled', 'wake_word', 'confidence_threshold', 'language']
    list_filter = ['enabled', 'language']
    search_fields = ['user__username']


@admin.register(VoiceCommandLog)
class VoiceCommandLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'intent', 'confidence', 'success', 'latency_ms', 'created_at']
    list_filter = ['success', 'intent', 'created_at']
    search_fields = ['user__username', 'raw_text', 'intent']
    readonly_fields = ['created_at']


@admin.register(KeywordSpotterModel)
class KeywordSpotterModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'architecture', 'version', 'accuracy', 'is_active', 'created_at']
    list_filter = ['architecture', 'is_active']
    search_fields = ['name']


@admin.register(TrainingDataset)
class TrainingDatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'num_samples', 'num_keywords', 'sample_rate', 'created_at']
    search_fields = ['name']


@admin.register(VoiceSession)
class VoiceSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'ended_at', 'total_commands', 'successful_commands']
    list_filter = ['started_at']
    search_fields = ['user__username']
