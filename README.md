<div align="center">

# Trutim

**Real-time chat, collaboration, and voice-controlled platform for engineers and developers.** Built on Django Channels (WebSockets), WebRTC, and a TensorFlow-powered keyword spotting engine for hands-free voice control.

## Features

- **Live Chat** — Real-time messaging with WebSockets, emoji reactions, typing indicators
- **Video Call** — WebRTC-based video conferencing with multiple participants
- **Screen Share** — Share your screen during calls
- **Strong Emojis** — Quick emoji bar + full emoji picker, message reactions
- **Voice Control** — Hands-free platform control via wake word detection and keyword spotting
- **Wake Word Engine** — Deep learning "Trutim" wake word detector with real-time streaming
- **Keyword Spotting** — 25-keyword vocabulary for voice commands (call, message, join, mute, etc.)
- **Automatic Speech Recognition** — CTC-based ASR with command-constrained decoding

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Django 4.x, Django REST Framework, Django Channels, Daphne (ASGI) |
| **Database** | PostgreSQL 15 |
| **Frontend** | React 19, Vite 7 |
| **Auth** | JWT (SimpleJWT) |
| **Real-time** | WebSockets (Channels), WebRTC |
| **Voice / ML** | TensorFlow, TensorFlow Lite, NumPy, SciPy |
| **DSP** | MFCC, Mel Spectrograms, Spectral Subtraction, Wiener Filtering, VAD |
| **Deep Learning** | DS-CNN, BiLSTM + Attention, TC-ResNet, Conformer, Multi-Head Spotter |

---

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [WebSocket Endpoints](#websocket-endpoints)
- [Development](#development)
- [Production Deployment](#production-deployment)

---

## Overview

Trutim is a **professional-grade collaboration platform** designed specifically for engineering teams and developers. Whether you're pair programming across time zones, conducting stand-ups, or debugging together—Trutim keeps everyone in sync with sub-second message delivery and crystal-clear video calls.

Built on a solid foundation of **Django Channels** (WebSockets) and **WebRTC**, the platform eliminates the friction of traditional communication tools. Messages appear instantly. Video connects peer-to-peer. And when you need a coding buddy, the in-app AI assistant is just one click away.

---

## Features

<img src="docs/assets/chat-lightning.svg" alt="Lightning-fast chat" width="80" height="80" align="right">

### Live Chat
Real-time messaging powered by WebSockets—no polling, no refresh. Messages are delivered instantly to all participants in a room. Supports persistent history, so you never lose context when rejoining a conversation.

### Video Calls
WebRTC-based peer-to-peer video conferencing with minimal latency. Start a call from any chat room; no external meeting links required. Built-in screen sharing lets you share your IDE, terminal, or browser during active calls.

### Emoji & Reactions
Express yourself with a quick emoji bar, full emoji picker, and message reactions. Because sometimes a 👍 says more than a paragraph.

### User Profiles
Custom profiles with username, email, and professional title. Upload avatars and manage your presence across the platform.

### Room Management
Create and join chat rooms with ease. Each room maintains its own message history and participant list. Organize by project, team, or topic.

<img src="docs/assets/ai-brain.svg" alt="AI Assistant" width="80" height="80" align="right">

### AI Assistant
An in-app AI chat panel powered by the **Vercel AI SDK** and **OpenAI** (streaming). Ask questions, get code suggestions, or brainstorm—without leaving the app. Optional; enable with your OpenAI API key.

### AI Image Generate
Generate images from text prompts directly in chat using **OpenAI DALL-E**. Click the image icon in the message toolbar, describe the image you want, and send it to the conversation.

### Share Code Panel
A dedicated panel for sharing code snippets. Click the code icon in the room header to open it. Paste code, optionally select a language, preview it, and share to chat with proper formatting.

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Django 4.x, Django REST Framework, Django Channels, Daphne |
| **Authentication** | JWT (Simple JWT) |
| **Database** | PostgreSQL (production) / SQLite (development) |
| **Real-time** | WebSockets, WebRTC |
| **Frontend** | React 19, Vite 7 |
| **AI Chat** | Vercel AI SDK (@ai-sdk/react), OpenAI API |
| **HTTP Client** | Axios |

---

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+
- **PostgreSQL** 15+ (optional for development; SQLite is used by default)
- **Redis** (optional; required for production WebSocket scaling)

---

## Quick Start

### 1. Clone and Install Dependencies

```bash
<<<<<<< HEAD
git clone <repository-url>
cd sean
=======
docker compose up -d db
>>>>>>> 9d4d154 (update chatting)
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows (CMD)
venv\Scripts\activate

# Windows (PowerShell) / Unix / macOS
source venv/bin/activate   # or: . venv/Scripts/activate on Windows Git Bash

pip install -r requirements.txt
```

### 3. Database Setup

**Option A: SQLite (default, no setup required)**

The project uses SQLite by default for development. No additional configuration needed—perfect for getting started quickly.

**Option B: PostgreSQL**

```bash
# Using Docker
docker-compose up -d db

# Or run PostgreSQL manually
docker run -d --name trutim-db \
  -e POSTGRES_DB=trutim_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine
```

Set `USE_SQLITE=False` and configure database environment variables (see [Configuration](#configuration)).

### 4. Run Migrations

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser   # Optional: for Django admin access
```

### 5. Start Backend Server

```bash
# ASGI server (required for WebSockets)
daphne -b 0.0.0.0 -p 8001 trutim.asgi:application
```

> **Note:** The frontend proxy expects the backend on port **8001**. Use `runserver` for API-only testing: `python manage.py runserver 8001`

### 6. Frontend Setup

```bash
# From project root
cd frontend
npm install
npm run dev
```

The application will be available at **http://localhost:5173**.

### 7. (Optional) Enable AI Assistant

To use the in-app AI chat panel, set your OpenAI API key:

```bash
# Unix / macOS / Git Bash
export OPENAI_API_KEY=sk-your-key-here

# Windows CMD
set OPENAI_API_KEY=sk-your-key-here
```

Then click the **AI** button in the header to open the assistant.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | (dev default) | Secret key for Django; **must be set in production** |
| `DEBUG` | `True` | Set to `False` in production |
| `USE_SQLITE` | `True` | Use SQLite (`True`) or PostgreSQL (`False`) |
| `DB_NAME` | `trutim_db` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `OPENAI_API_KEY` | — | OpenAI API key for the AI Assistant and AI Image Generate (optional) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for chat (e.g. `gpt-4o`, `gpt-4o-mini`) |
| `OPENAI_IMAGE_MODEL` | `dall-e-3` | OpenAI model for image generation |

### Example: PostgreSQL Configuration

```bash
# Windows CMD
set USE_SQLITE=False
set DB_NAME=trutim_db
set DB_USER=postgres
set DB_PASSWORD=postgres
set DB_HOST=localhost
set DB_PORT=5432

# Unix / macOS / Git Bash
export USE_SQLITE=False
export DB_NAME=trutim_db
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=5432
```

For production, use a `.env` file with `python-dotenv` or your deployment platform's secrets manager.

<<<<<<< HEAD
=======
```bash
python manage.py makemigrations voice
python manage.py migrate
python manage.py createsuperuser   # optional, for admin
```

For development (HTTP only):

```bash
python manage.py runserver 0.0.0.0:8000
```

For production (HTTP + WebSockets via ASGI):

```bash
daphne -b 0.0.0.0 -p 8000 trutim.asgi:application
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies API/WS to the backend.

---

## Voice Control System

### Overview

The voice control system enables hands-free operation of the entire Trutim platform through speech. It uses a multi-stage pipeline:

```
Microphone Audio
    │
    ▼
┌──────────────────────┐
│  Audio Preprocessing  │  Resampling, DC blocking, pre-emphasis,
│  (DSP Pipeline)       │  normalization, dithering
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Noise Reduction      │  Spectral subtraction, Wiener filtering,
│  + VAD                │  Voice Activity Detection
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Feature Extraction   │  MFCC, Mel spectrograms, delta features,
│                       │  spectral centroid/bandwidth/rolloff
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Wake Word Detector   │  CNN/RNN model detects "Trutim"
│  (Always Listening)   │  Confidence smoothing + debouncing
└──────────┬───────────┘
           │ wake word detected
           ▼
┌──────────────────────┐
│  Keyword Spotter      │  Multi-keyword detection from 25-word
│  (Command Window)     │  vocabulary, sliding window analysis
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  ASR + Language Model │  CTC-based speech recognition,
│                       │  command-constrained decoding
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Intent Classifier    │  Multi-strategy classification:
│                       │  exact match → keyword → pattern → fuzzy
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Entity Extractor     │  Resolve users, rooms, text content
│                       │  against the database
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Command Executor     │  Execute platform actions via
│                       │  Django ORM + Channels
└──────────────────────┘
```

### Supported Voice Commands

| Command | Example Phrases | Action |
|---------|----------------|--------|
| **Call** | "call john", "call user sarah" | Start a voice call |
| **Video Call** | "video call", "start video call" | Start a video call |
| **Send Message** | "send message to john", "message sarah" | Send a text message |
| **Join Room** | "join room general", "join engineering" | Join a chat room |
| **Leave Room** | "leave room", "exit" | Leave current room |
| **Create Room** | "create room standup" | Create a new room |
| **Mute** | "mute", "mute microphone" | Mute microphone |
| **Unmute** | "unmute", "unmute mic" | Unmute microphone |
| **Camera** | "toggle camera", "mute camera" | Toggle camera on/off |
| **Screen Share** | "share screen", "screen share" | Start screen sharing |
| **Stop Share** | "stop share", "stop screen share" | Stop screen sharing |
| **Select User** | "select user john", "select sarah" | Select a user |
| **Open Room** | "open room general", "go to design" | Navigate to a room |
| **Go Back** | "go back", "back" | Navigate back |
| **End Call** | "end call", "hang up" | End the current call |
| **Confirm** | "yes", "confirm", "okay" | Confirm pending action |
| **Cancel** | "no", "cancel", "stop" | Cancel pending action |
| **Broadcast** | "send to everyone", "broadcast" | Message all room members |

### Keyword Vocabulary (25 keywords)

```
trutim   call     message  send     video    join     leave    create
room     mute     unmute   camera   screen   share    select   open
close    back     user     everyone yes      no       cancel   confirm
_silence
```

### Model Architectures

| Architecture | Parameters | Strengths | Use Case |
|-------------|-----------|-----------|----------|
| **DS-CNN** | ~80K | Lightweight, fast inference | On-device / edge deployment |
| **Attention-RNN** | ~250K | High accuracy, BiLSTM + MHA | Balanced accuracy/speed |
| **TC-ResNet** | ~150K | Causal convolutions, streaming | Real-time streaming detection |
| **Conformer** | ~500K | CNN + Transformer hybrid | Highest accuracy (server-side) |
| **Multi-Head** | ~350K | Simultaneous wake + command detection | Combined wake word + keyword spotting |

### Training Pipeline

#### 1. Generate Training Data

Produces synthetic training data using formant-based voice synthesis with diverse speaker profiles, noise conditions, and room acoustics.

```bash
# Default: 2000 samples/keyword, 50 speakers
python manage.py generate_training_data

# Large-scale: 5000 samples/keyword, 100 speakers
python manage.py generate_training_data --samples-per-keyword 5000 --speakers 100

# Specific keywords only
python manage.py generate_training_data --keywords trutim call message video
```

**Data generation features:**
- 50+ simulated speaker profiles (male/female, varying pitch, breathiness, jitter)
- 10 noise types: white, pink, brown, babble, office, traffic, music, keyboard, fan, rain
- SNR range: 5–30 dB
- Room acoustics: small room, medium room, large room, concert hall
- Speed perturbation: 0.8x–1.3x
- Pitch variation: 0.7x–1.4x
- Silence and unknown-word negative samples

#### 2. Train a Model

```bash
# Train DS-CNN (fast, lightweight)
python manage.py train_wake_word --architecture ds_cnn --epochs 100 --activate

# Train Conformer (best accuracy)
python manage.py train_wake_word --architecture conformer --epochs 200 --batch-size 32 --activate

# Train Attention-RNN with custom learning rate
python manage.py train_wake_word --architecture attention_rnn --epochs 150 --lr 0.0005

# Train TC-ResNet for streaming
python manage.py train_wake_word --architecture tc_resnet --epochs 100 --activate
```

**Training features:**
- Cosine annealing with warm restarts learning rate schedule
- Label smoothing (0.1) for better generalization
- SpecAugment (frequency + time masking)
- Audio augmentation (time shift, speed perturbation, pitch shift, gain, noise injection)
- Mixup data augmentation
- Class-weighted loss for imbalanced datasets
- Early stopping + best-model checkpointing
- TensorBoard logging
- Automatic TF Lite export with quantization (dynamic, float16, int8)

#### 3. TF Lite Export

Models are automatically exported to TF Lite during training with multiple quantization options:

| Quantization | Model Size | Inference Speed | Accuracy |
|-------------|-----------|----------------|----------|
| None (float32) | Baseline | Baseline | Best |
| Dynamic range | ~4x smaller | ~2x faster | Near-best |
| Float16 | ~2x smaller | ~1.5x faster | Near-best |
| Full int8 | ~4x smaller | ~3x faster | Slightly reduced |

### DSP Pipeline Details

#### Audio Preprocessing (`voice/dsp/audio_processor.py`)

| Stage | Description |
|-------|-------------|
| Decoding | PCM16, PCM24, PCM32, float32, WAV format support |
| Channel mixing | Stereo → mono averaging |
| Resampling | Polyphase interpolation (arbitrary rate conversion) |
| DC blocking | IIR filter: `y[n] = x[n] - x[n-1] + R·y[n-1]` |
| Dithering | TPDF (Triangular Probability Density Function) |
| Pre-emphasis | High-pass: `y[n] = x[n] - 0.97·x[n-1]` |
| Normalization | Peak normalize to [-1, 1] |
| Framing | 25ms frames, 10ms hop, Hann/Hamming/Blackman window |

#### Feature Extraction (`voice/dsp/feature_extraction.py`)

| Feature | Dimensions | Description |
|---------|-----------|-------------|
| Mel spectrogram | (frames, 80) | 80 mel-spaced triangular filterbank bins |
| Log filterbank | (frames, 80) | Log-compressed mel energies |
| MFCC | (frames, 13) | DCT-II of log mel, cepstral liftering |
| MFCC + delta | (frames, 26) | MFCC + first derivative |
| MFCC + delta + delta-delta | (frames, 39) | Full MFCC feature set |
| Spectral features | (frames, 4) | Centroid, bandwidth, rolloff, flux |
| Full features | (frames, 123) | All of the above concatenated |

#### Noise Reduction (`voice/dsp/noise_reduction.py`)

1. **Noise profile estimation** — from initial silence or provided noise sample
2. **Spectral subtraction** — `|Y|² = max(|X|² - α·|N|², β·|N|²)` with oversubtraction factor
3. **Wiener filter** — `H = |S|² / (|S|² + β·|N|²)` for residual suppression
4. **Spectral smoothing** — temporal smoothing to reduce musical noise artifacts

#### Voice Activity Detection (`voice/dsp/noise_reduction.py`)

- Energy-based detection with adaptive thresholding
- Zero-crossing rate analysis
- Finite state machine: SILENCE → SPEECH_START → SPEECH → SPEECH_END
- Hangover logic to prevent premature cutoff
- Configurable speech/silence duration thresholds
- Segment merging for close speech regions

---

## Usage

### Web UI

1. **Register** — Create an account with username, email, title (e.g. Senior Engineer)
2. **Create Room** — From the dashboard, create a new room
3. **Chat** — Send messages, use quick emojis or the full picker
4. **Video Call** — Click the video icon in a room to start a call
5. **Screen Share** — Use the screen share button during a video call

### Voice Control (WebSocket)

Connect to the voice control WebSocket and stream audio:

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/voice/${roomId}/?token=${jwt}`);

// Start listening for wake word
ws.send(JSON.stringify({ type: 'start_listening' }));

// Stream audio chunks (PCM16, base64-encoded)
ws.send(JSON.stringify({
  type: 'audio_data',
  data: base64PCM16Audio,
  sample_rate: 16000,
}));

// Or send raw binary PCM16 audio directly
ws.send(pcm16ArrayBuffer);

// Or send text commands directly (bypass audio pipeline)
ws.send(JSON.stringify({ type: 'text_command', text: 'call john' }));

// Or send spotted keywords
ws.send(JSON.stringify({
  type: 'keyword_command',
  keywords: ['call', 'user', 'john'],
}));

// Listen for events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'wake_word_detected':
      // { confidence: 0.95 } — system is listening for command
      break;
    case 'keyword_spotted':
      // { keywords: [{ keyword: 'call', confidence: 0.92 }] }
      break;
    case 'command_result':
      // { result: { success: true, command: 'call_user', message: 'Calling john...' } }
      break;
    case 'listening_state':
      // { state: 'listening' | 'stopped', message: '...' }
      break;
    case 'command_timeout':
      // Command window expired without valid command
      break;
  }
};

// Get current status
ws.send(JSON.stringify({ type: 'get_status' }));

// Update configuration
ws.send(JSON.stringify({
  type: 'update_config',
  config: { confidence_threshold: 0.9 },
}));

// Stop listening
ws.send(JSON.stringify({ type: 'stop_listening' }));
```

### Voice Control REST API

```bash
# Execute a voice command (text-based)
curl -X POST http://localhost:8000/api/voice/execute/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "call john", "room_id": 1}'

# Get voice system info (keywords, commands, models)
curl http://localhost:8000/api/voice/system/ \
  -H "Authorization: Bearer $TOKEN"

# Get/update your voice profile
curl http://localhost:8000/api/voice/profiles/me/ \
  -H "Authorization: Bearer $TOKEN"

curl -X PATCH http://localhost:8000/api/voice/profiles/update_settings/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confidence_threshold": 0.9, "wake_word": "trutim"}'

# View command history
curl http://localhost:8000/api/voice/commands/log/ \
  -H "Authorization: Bearer $TOKEN"

# Command stats
curl http://localhost:8000/api/voice/commands/log/stats/ \
  -H "Authorization: Bearer $TOKEN"

# List keyword spotting models
curl http://localhost:8000/api/voice/models/ \
  -H "Authorization: Bearer $TOKEN"

# Activate a model
curl -X POST http://localhost:8000/api/voice/models/1/activate/ \
  -H "Authorization: Bearer $TOKEN"

# Benchmark a model
curl http://localhost:8000/api/voice/models/1/benchmark/ \
  -H "Authorization: Bearer $TOKEN"

# Trigger training data generation
curl -X POST http://localhost:8000/api/voice/generate-data/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"samples_per_keyword": 5000, "num_speakers": 100}'

# Trigger model training
curl -X POST http://localhost:8000/api/voice/train/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"architecture": "ds_cnn", "epochs": 100, "batch_size": 64}'
```

>>>>>>> 9d4d154 (update chatting)
---

## Project Structure

```
sean/
├── backend/
<<<<<<< HEAD
│   ├── chat/                 # Chat application
│   │   ├── ai_views.py       # AI chat streaming endpoint
│   │   ├── consumers.py      # WebSocket consumers (chat, call signaling)
│   │   ├── middleware.py     # JWT auth for WebSockets
│   │   ├── models.py         # User, Room, Message
│   │   ├── routing.py        # WebSocket URL routing
│   │   ├── serializers.py    # DRF serializers
│   │   ├── urls.py           # REST API routes
│   │   └── views.py          # API views
│   ├── trutim/               # Django project settings
│   │   ├── asgi.py           # ASGI application (Channels)
│   │   ├── settings.py
│   │   └── urls.py
=======
│   ├── trutim/                         # Django project config
│   │   ├── asgi.py                     # ASGI app (HTTP + WebSocket routing)
│   │   ├── settings.py                 # Django settings + voice config
│   │   ├── urls.py                     # Root URL config
│   │   └── wsgi.py                     # WSGI app
│   │
│   ├── chat/                           # Chat & video call app
│   │   ├── models.py                   # User, Room, Message, CallSession
│   │   ├── views.py                    # REST API views
│   │   ├── consumers.py                # WebSocket consumers (Chat, Call)
│   │   ├── routing.py                  # WebSocket URL routing
│   │   ├── serializers.py              # DRF serializers
│   │   ├── middleware.py               # JWT auth for WebSockets
│   │   ├── urls.py                     # API routes
│   │   └── admin.py                    # Admin registration
│   │
│   ├── voice/                          # Voice Control & Keyword Spotting
│   │   ├── dsp/                        # Digital Signal Processing
│   │   │   ├── audio_processor.py      # Audio pipeline: decode, resample, pre-emphasis
│   │   │   ├── feature_extraction.py   # MFCC, Mel spectrograms, spectral features
│   │   │   └── noise_reduction.py      # Noise reduction, Wiener filter, VAD
│   │   │
│   │   ├── engine/                     # Deep Learning Engine
│   │   │   ├── model_architecture.py   # 5 TF model architectures
│   │   │   ├── wake_word_detector.py   # Real-time wake word detection
│   │   │   ├── keyword_spotter.py      # Multi-keyword spotting (25 keywords)
│   │   │   └── inference_engine.py     # TF Lite inference + quantization
│   │   │
│   │   ├── training/                   # Training Pipeline
│   │   │   ├── data_generator.py       # Synthetic training data generation
│   │   │   ├── augmentation.py         # Audio + spectrogram augmentation
│   │   │   ├── dataset_builder.py      # tf.data.Dataset construction
│   │   │   └── trainer.py              # Full training pipeline
│   │   │
│   │   ├── asr/                        # Automatic Speech Recognition
│   │   │   ├── speech_recognizer.py    # CTC-based ASR engine
│   │   │   └── language_model.py       # Command language model (n-gram)
│   │   │
│   │   ├── commands/                   # Voice Command System
│   │   │   ├── command_registry.py     # 18 registered voice commands
│   │   │   ├── intent_classifier.py    # Multi-strategy intent classification
│   │   │   ├── entity_extractor.py     # User/room/text entity resolution
│   │   │   └── command_executor.py     # Command execution via ORM + Channels
│   │   │
│   │   ├── management/commands/        # Django Management Commands
│   │   │   ├── generate_training_data.py
│   │   │   └── train_wake_word.py
│   │   │
│   │   ├── models.py                   # VoiceProfile, CommandLog, KWSModel, etc.
│   │   ├── views.py                    # REST API for voice control
│   │   ├── serializers.py              # DRF serializers
│   │   ├── urls.py                     # Voice API routes
│   │   ├── consumers.py                # WebSocket consumer (voice streaming)
│   │   ├── routing.py                  # Voice WebSocket URL routing
│   │   └── admin.py                    # Admin registration
│   │
>>>>>>> 9d4d154 (update chatting)
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
<<<<<<< HEAD
│   │   ├── components/       # AIPromptPanel, EmojiPicker, VideoCall
│   │   ├── context/          # AuthContext
│   │   ├── hooks/            # useChatSocket, useCallSocket
│   │   ├── pages/            # Login, Register, Dashboard, Room
│   │   └── api.js            # Axios API client
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── assets/               # README illustrations
├── docker-compose.yml        # PostgreSQL service
=======
│   │   ├── components/                 # EmojiPicker, VideoCall
│   │   ├── context/                    # AuthContext
│   │   ├── hooks/                      # useChatSocket, useCallSocket
│   │   └── pages/                      # Login, Register, Dashboard, Room
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
>>>>>>> 9d4d154 (update chatting)
└── README.md
```

---

## API Reference

<<<<<<< HEAD
Base URL: `http://localhost:8001/api` (or your backend host)

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register/` | Register a new user |
| `POST` | `/api/auth/login/` | Login; returns JWT access and refresh tokens |
| `POST` | `/api/auth/refresh/` | Refresh access token |

### Protected Endpoints (require `Authorization: Bearer <token>`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rooms/` | List rooms |
| `POST` | `/api/rooms/` | Create a room |
| `GET` | `/api/messages/?room=<id>` | List messages for a room |
| `GET` | `/api/users/` | List users (ViewSet) |
| `POST` | `/api/ai/chat/` | AI chat (streaming; requires `OPENAI_API_KEY`) |
| `POST` | `/api/ai/image/` | AI image generation (DALL-E; requires `OPENAI_API_KEY`) |

---

## WebSocket Endpoints

<img src="docs/assets/realtime-rocket.svg" alt="Real-time rocket" width="60" height="60" align="right">

| Endpoint | Purpose |
|----------|---------|
| `ws://host:8001/ws/chat/<room_id>/?token=<jwt>` | Real-time chat messaging |
| `ws://host:8001/ws/call/<room_id>/?token=<jwt>` | WebRTC signaling for video calls |

Include the JWT access token in the `token` query parameter for authentication.

---

## Development

### Root Scripts

From the project root:

```bash
npm run dev      # Start frontend dev server
npm run build    # Build frontend for production
npm run preview  # Preview production build
```

### Linting

```bash
cd frontend
npm run lint
```

### Django Admin

Access the admin panel at `http://localhost:8001/admin/` after creating a superuser.

---

## Production Deployment

1. **Set production environment variables:**
   - `DEBUG=False`
   - `DJANGO_SECRET_KEY` (generate a secure random key)
   - Configure `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
   - `OPENAI_API_KEY` (optional; for AI Assistant)

2. **Use PostgreSQL** (set `USE_SQLITE=False` and configure `DB_*` variables).

3. **Use Redis for Channels** (required for multi-worker/multi-server):
   ```python
   CHANNEL_LAYERS = {
       'default': {
           'BACKEND': 'channels_redis.core.RedisChannelLayer',
           'CONFIG': {'hosts': [('redis-host', 6379)]},
       }
   }
   ```

4. **Serve static files:** Run `python manage.py collectstatic` and configure your web server (e.g., Nginx) to serve them.

5. **Build frontend:** `npm run build` and serve the `frontend/dist` output via your web server or CDN.

6. **Use a production ASGI server:** Daphne, Uvicorn, or Hypercorn behind a reverse proxy (Nginx, Caddy).

---

## License

Proprietary. All rights reserved.
=======
### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login (returns JWT) |
| POST | `/api/auth/refresh/` | Refresh JWT token |
| GET | `/api/users/` | List users |
| GET | `/api/users/me/` | Current user profile |
| GET | `/api/rooms/` | List rooms |
| POST | `/api/rooms/` | Create room |
| POST | `/api/rooms/{id}/join/` | Join room |
| POST | `/api/rooms/{id}/leave/` | Leave room |
| GET | `/api/messages/?room={id}` | List messages |
| POST | `/api/messages/{id}/react/` | Add/remove reaction |

### Voice Control API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/voice/execute/` | Execute voice command (text/keywords) |
| GET | `/api/voice/system/` | System info, keywords, available commands |
| GET | `/api/voice/profiles/me/` | Get user voice profile |
| PATCH | `/api/voice/profiles/update_settings/` | Update voice settings |
| GET | `/api/voice/commands/log/` | Command history |
| GET | `/api/voice/commands/log/stats/` | Command analytics |
| GET | `/api/voice/models/` | List KWS models |
| POST | `/api/voice/models/{id}/activate/` | Activate a model |
| GET | `/api/voice/models/{id}/benchmark/` | Benchmark model inference |
| GET | `/api/voice/models/active/` | Get active model |
| POST | `/api/voice/train/` | Queue model training |
| POST | `/api/voice/generate-data/` | Queue data generation |
| GET | `/api/voice/datasets/` | List training datasets |
| GET | `/api/voice/sessions/` | List voice sessions |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/chat/{room_id}/?token={jwt}` | Live chat (messages, typing, presence) |
| `ws://host/ws/call/{room_id}/?token={jwt}` | WebRTC signaling (offer, answer, ICE) |
| `ws://host/ws/voice/{room_id}/?token={jwt}` | Voice control (audio streaming, commands) |
| `ws://host/ws/voice/?token={jwt}` | Voice control (no room context) |

---

## Database Models

### Chat Models

- **User** — Extended Django user with title, avatar, online status
- **Room** — Chat room with name, description, members, direct message flag
- **Message** — Chat message with emoji reactions (JSON)
- **CallSession** — Video call session tracking

### Voice Models

- **VoiceProfile** — Per-user voice settings (wake word, confidence threshold, noise reduction level, language)
- **VoiceCommandLog** — Audit log of all voice commands (intent, confidence, entities, result, latency)
- **KeywordSpotterModel** — Registry of trained models (architecture, accuracy, TFLite path, active flag)
- **TrainingDataset** — Generated training dataset metadata (samples, keywords, manifest)
- **VoiceSession** — Voice control session tracking (duration, command counts, wake detections)

---

## Dependencies

### Backend (`requirements.txt`)

| Package | Purpose |
|---------|---------|
| Django 4.x | Web framework |
| djangorestframework | REST API |
| django-cors-headers | CORS for React frontend |
| psycopg2-binary | PostgreSQL adapter |
| channels | WebSocket support (ASGI) |
| channels-redis | Redis channel layer (production) |
| daphne | ASGI server |
| djangorestframework-simplejwt | JWT authentication |
| Pillow | Image processing (avatars) |
| tensorflow | Deep learning models, TF Lite |
| tensorflow-io | Audio I/O utilities |
| numpy | Numerical computation |
| scipy | Signal processing |

### Frontend (`package.json`)

| Package | Purpose |
|---------|---------|
| react 19 | UI framework |
| react-dom | DOM rendering |
| react-router-dom | Client-side routing |
| axios | HTTP client |
| emoji-picker-element | Emoji picker component |
| vite | Build tool / dev server |
>>>>>>> 9d4d154 (update chatting)
