"""
Voice Control WebSocket Consumer — real-time voice streaming.

Handles bidirectional audio streaming for:
1. Wake word detection (always listening)
2. Keyword spotting (after wake word)
3. Command recognition and execution
4. Voice feedback to client
"""
import json
import time
import base64
import logging
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from .engine.wake_word_detector import WakeWordDetector, WakeWordConfig, DetectorState
from .engine.keyword_spotter import KeywordSpotter, SpotterConfig
from .engine.inference_engine import InferenceEngine
from .dsp.audio_processor import AudioConfig, StreamingAudioBuffer
from .dsp.feature_extraction import FeatureExtractor, FeatureConfig
from .dsp.noise_reduction import NoiseReducer
from .commands.command_executor import CommandExecutor
from .commands.intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)
User = get_user_model()


class VoiceControlConsumer(AsyncWebsocketConsumer):
    """
    Real-time voice control WebSocket consumer.

    Protocol:
    Client -> Server:
        - {"type": "audio_data", "data": "<base64 PCM16>", "sample_rate": 16000}
        - {"type": "text_command", "text": "call john"}
        - {"type": "start_listening"}
        - {"type": "stop_listening"}
        - {"type": "get_status"}
        - {"type": "update_config", "config": {...}}

    Server -> Client:
        - {"type": "wake_word_detected", "confidence": 0.95}
        - {"type": "keyword_spotted", "keywords": [...]}
        - {"type": "command_result", "result": {...}}
        - {"type": "listening_state", "state": "..."}
        - {"type": "status", "data": {...}}
        - {"type": "error", "message": "..."}
        - {"type": "vad_state", "speaking": true/false}
    """

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        self.voice_group = f'voice_{self.user.id}'

        audio_config = AudioConfig()

        self.wake_detector = WakeWordDetector(
            wake_config=WakeWordConfig(),
            audio_config=audio_config,
        )
        self.keyword_spotter = KeywordSpotter(
            config=SpotterConfig(),
            audio_config=audio_config,
        )
        self.command_executor = CommandExecutor()
        self.noise_reducer = NoiseReducer(audio_config)
        self.audio_buffer = StreamingAudioBuffer(
            audio_config,
            window_duration_ms=1000.0,
            overlap_duration_ms=200.0,
        )

        self.wake_detector.register_callback(self._on_wake_word)

        self._session_start = time.time()
        self._command_count = 0
        self._successful_commands = 0
        self._total_audio_s = 0.0
        self._wake_detections = 0
        self._is_listening = False
        self._command_audio_buffer = []
        self._awaiting_command = False

        self._load_models()

        await self.channel_layer.group_add(self.voice_group, self.channel_name)
        await self.accept()
        await self._create_session()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Voice control connected. Say "Trutim" to activate.',
            'wake_word': 'trutim',
        }))

        logger.info("Voice control connected for user %s", self.user.username)

    async def disconnect(self, close_code):
        if hasattr(self, 'voice_group'):
            await self.channel_layer.group_discard(self.voice_group, self.channel_name)

        if hasattr(self, '_session_start'):
            await self._end_session()

        self.wake_detector.stop()
        logger.info("Voice control disconnected for user %s",
                     getattr(self, 'user', {}).username if hasattr(self, 'user') else 'unknown')

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages."""
        if bytes_data:
            await self._process_binary_audio(bytes_data)
            return

        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        msg_type = data.get('type', '')
        handlers = {
            'audio_data': self._handle_audio_data,
            'text_command': self._handle_text_command,
            'start_listening': self._handle_start_listening,
            'stop_listening': self._handle_stop_listening,
            'get_status': self._handle_get_status,
            'update_config': self._handle_update_config,
            'keyword_command': self._handle_keyword_command,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(data)
        else:
            await self._send_error(f"Unknown message type: {msg_type}")

    # --- Message Handlers ---

    async def _handle_audio_data(self, data):
        """Process base64-encoded audio data."""
        audio_b64 = data.get('data', '')
        sample_rate = data.get('sample_rate', 16000)

        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            await self._send_error("Invalid base64 audio data")
            return

        await self._process_audio(audio_bytes, sample_rate)

    async def _process_binary_audio(self, audio_bytes):
        """Process raw binary audio data."""
        await self._process_audio(audio_bytes, 16000)

    async def _process_audio(self, audio_bytes, sample_rate):
        """Core audio processing pipeline."""
        self._total_audio_s += len(audio_bytes) / (sample_rate * 2)  # PCM16 = 2 bytes/sample

        if not self._is_listening:
            return

        if self._awaiting_command:
            self._command_audio_buffer.append(audio_bytes)

            windows = self.audio_buffer.add_chunk(audio_bytes, sample_rate)
            for window in windows:
                spotted = self.keyword_spotter.spot_keywords_streaming(
                    window, time.time() * 1000
                )
                if spotted:
                    await self.send(text_data=json.dumps({
                        'type': 'keyword_spotted',
                        'keywords': [
                            {'keyword': s.keyword, 'confidence': s.confidence}
                            for s in spotted
                        ],
                    }))

            if self.wake_detector.check_command_timeout():
                await self._finalize_command()
            return

        result = self.wake_detector.process_audio_chunk(audio_bytes, sample_rate)
        if result:
            self._wake_detections += 1
            self._awaiting_command = True
            self._command_audio_buffer.clear()
            self.audio_buffer.reset()
            self.keyword_spotter.clear_buffer()

    async def _handle_text_command(self, data):
        """Execute a text-based voice command."""
        text = data.get('text', '').strip()
        if not text:
            await self._send_error("No command text provided")
            return

        room_id = data.get('room_id', self.room_id)
        result = await self.command_executor.execute_from_text(
            text, self.user, room_id
        )

        self._command_count += 1
        if result.success:
            self._successful_commands += 1

        await self._log_command(
            text, result.command, 0.9, result.success,
            result.data, []
        )

        await self.send(text_data=json.dumps({
            'type': 'command_result',
            'result': result.to_dict(),
        }))

    async def _handle_keyword_command(self, data):
        """Execute command from spotted keywords."""
        keywords = data.get('keywords', [])
        if not keywords:
            await self._send_error("No keywords provided")
            return

        room_id = data.get('room_id', self.room_id)
        result = await self.command_executor.execute_from_keywords(
            keywords, self.user, room_id
        )

        self._command_count += 1
        if result.success:
            self._successful_commands += 1

        await self.send(text_data=json.dumps({
            'type': 'command_result',
            'result': result.to_dict(),
        }))

    async def _handle_start_listening(self, data):
        """Start the voice detection pipeline."""
        self._is_listening = True
        self.wake_detector.start()

        await self.send(text_data=json.dumps({
            'type': 'listening_state',
            'state': 'listening',
            'message': 'Listening for wake word "Trutim"...',
        }))

    async def _handle_stop_listening(self, data):
        """Stop the voice detection pipeline."""
        self._is_listening = False
        self.wake_detector.stop()
        self._awaiting_command = False

        await self.send(text_data=json.dumps({
            'type': 'listening_state',
            'state': 'stopped',
            'message': 'Voice control paused.',
        }))

    async def _handle_get_status(self, data):
        """Return current voice control status."""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': {
                'listening': self._is_listening,
                'detector_state': self.wake_detector.state.name,
                'awaiting_command': self._awaiting_command,
                'session_duration_s': time.time() - self._session_start,
                'total_audio_s': self._total_audio_s,
                'commands_executed': self._command_count,
                'successful_commands': self._successful_commands,
                'wake_detections': self._wake_detections,
            }
        }))

    async def _handle_update_config(self, data):
        """Update voice control configuration."""
        config = data.get('config', {})

        if 'confidence_threshold' in config:
            self.wake_detector.wake_config.confidence_threshold = config['confidence_threshold']
        if 'wake_word' in config:
            self.wake_detector.wake_config.wake_word = config['wake_word']

        await self.send(text_data=json.dumps({
            'type': 'config_updated',
            'message': 'Configuration updated.',
        }))

    # --- Internal methods ---

    def _on_wake_word(self, result):
        """Callback when wake word is detected (sync context)."""
        pass  # Actual notification sent in _process_audio

    async def _finalize_command(self):
        """Finalize command after keyword collection timeout."""
        command = self.keyword_spotter.assemble_command()

        if command:
            result = await self.command_executor.execute_from_keywords(
                [kw['keyword'] for kw in command['keywords']],
                self.user, self.room_id,
            )

            self._command_count += 1
            if result.success:
                self._successful_commands += 1

            await self.send(text_data=json.dumps({
                'type': 'command_result',
                'result': result.to_dict(),
                'assembled_command': command,
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'command_timeout',
                'message': "Didn't catch a command. Try again.",
            }))

        self._awaiting_command = False
        self._command_audio_buffer.clear()
        self.wake_detector.return_to_listening()

        await self.send(text_data=json.dumps({
            'type': 'listening_state',
            'state': 'listening',
            'message': 'Listening for wake word...',
        }))

    def _load_models(self):
        """Load keyword spotting models if available."""
        try:
            from .models import KeywordSpotterModel as KWSModel
            active = KWSModel.objects.filter(is_active=True).first()
            if active:
                engine = InferenceEngine()
                if active.tflite_path:
                    engine.load_tflite_model('active_kws', active.tflite_path)
                elif active.model_path:
                    engine.load_tf_model('active_kws', active.model_path)
        except Exception as e:
            logger.warning("Could not load KWS model: %s", e)

    @database_sync_to_async
    def _create_session(self):
        from .models import VoiceSession
        self._session = VoiceSession.objects.create(
            user=self.user,
            room_id=self.room_id,
        )

    @database_sync_to_async
    def _end_session(self):
        from .models import VoiceSession
        if hasattr(self, '_session'):
            VoiceSession.objects.filter(id=self._session.id).update(
                ended_at=timezone.now(),
                total_commands=self._command_count,
                successful_commands=self._successful_commands,
                total_audio_duration_s=self._total_audio_s,
                wake_word_detections=self._wake_detections,
            )

    @database_sync_to_async
    def _log_command(self, raw_text, intent, confidence, success, result, keywords):
        from .models import VoiceCommandLog
        VoiceCommandLog.objects.create(
            user=self.user,
            room_id=self.room_id,
            raw_text=raw_text,
            intent=intent,
            confidence=confidence,
            success=success,
            command_result=result or {},
            keywords_spotted=keywords or [],
        )

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))
