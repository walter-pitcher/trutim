"""
Voice Control Models — persistent storage for voice system state.

Tracks voice commands, keyword spotting sessions, model configurations,
and training data metadata.
"""
from django.db import models
from django.conf import settings


class VoiceProfile(models.Model):
    """Per-user voice control configuration and calibration data."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='voice_profile'
    )
    enabled = models.BooleanField(default=True)
    wake_word = models.CharField(max_length=50, default='trutim')
    confidence_threshold = models.FloatField(default=0.85)
    noise_reduction_level = models.CharField(
        max_length=20, default='medium',
        choices=[('off', 'Off'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    )
    language = models.CharField(max_length=10, default='en')
    use_vad = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trutim_voice_profiles'

    def __str__(self):
        return f"VoiceProfile({self.user.username})"


class VoiceCommandLog(models.Model):
    """Log of executed voice commands for analytics and improvement."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='voice_commands'
    )
    room = models.ForeignKey(
        'chat.Room', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='voice_commands'
    )
    raw_text = models.TextField(blank=True)
    intent = models.CharField(max_length=100)
    confidence = models.FloatField(default=0.0)
    entities = models.JSONField(default=dict, blank=True)
    command_result = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    latency_ms = models.FloatField(default=0.0)
    keywords_spotted = models.JSONField(default=list, blank=True)
    wake_word_confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trutim_voice_command_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"VoiceCommand({self.user.username}: {self.intent})"


class KeywordSpotterModel(models.Model):
    """Registry of trained keyword spotting models."""
    name = models.CharField(max_length=200, unique=True)
    architecture = models.CharField(
        max_length=50,
        choices=[
            ('ds_cnn', 'DS-CNN'),
            ('attention_rnn', 'Attention RNN'),
            ('tc_resnet', 'TC-ResNet'),
            ('conformer', 'Conformer'),
            ('multi_head', 'Multi-Head'),
        ]
    )
    version = models.CharField(max_length=50, default='1.0.0')
    model_path = models.CharField(max_length=500)
    tflite_path = models.CharField(max_length=500, blank=True)
    num_parameters = models.IntegerField(default=0)
    num_keywords = models.IntegerField(default=25)
    accuracy = models.FloatField(default=0.0)
    training_epochs = models.IntegerField(default=0)
    training_samples = models.IntegerField(default=0)
    is_active = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trutim_kws_models'
        ordering = ['-created_at']

    def __str__(self):
        status = 'active' if self.is_active else 'inactive'
        return f"KWSModel({self.name} [{status}])"


class TrainingDataset(models.Model):
    """Metadata for generated training datasets."""
    name = models.CharField(max_length=200)
    data_dir = models.CharField(max_length=500)
    num_samples = models.IntegerField(default=0)
    num_keywords = models.IntegerField(default=0)
    sample_rate = models.IntegerField(default=16000)
    duration_per_sample_s = models.FloatField(default=1.0)
    manifest = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trutim_training_datasets'

    def __str__(self):
        return f"Dataset({self.name}: {self.num_samples} samples)"


class VoiceSession(models.Model):
    """Active voice control session tracking."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='voice_sessions'
    )
    room = models.ForeignKey(
        'chat.Room', on_delete=models.SET_NULL, null=True, blank=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    total_commands = models.IntegerField(default=0)
    successful_commands = models.IntegerField(default=0)
    total_audio_duration_s = models.FloatField(default=0.0)
    wake_word_detections = models.IntegerField(default=0)

    class Meta:
        db_table = 'trutim_voice_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"VoiceSession({self.user.username}, {self.started_at})"
