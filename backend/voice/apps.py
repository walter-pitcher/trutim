from django.apps import AppConfig


class VoiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voice'
    verbose_name = 'Voice Control & Keyword Spotting'

    def ready(self):
        from .commands.command_registry import CommandRegistry
        CommandRegistry.auto_discover()
