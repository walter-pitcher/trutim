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

<p align="center">
  <img src="docs/screenshots/Screenshot%202026-03-24%20110819.png" alt="Register screen with Google and GitHub OAuth options" width="560" />
</p>

### Room Management
Create and join chat rooms with ease. Each room maintains its own message history and participant list. Organize by project, team, or topic.

<p align="center">
  <img src="docs/screenshots/Screenshot%202026-03-24%20111404.png" alt="Main chat workspace with contacts and message composer" width="900" />
</p>

<img src="docs/assets/ai-brain.svg" alt="AI Assistant" width="80" height="80" align="right">

### AI Assistant
An in-app AI chat panel powered by the **Vercel AI SDK** and **OpenAI** (streaming). Ask questions, get code suggestions, or brainstorm—without leaving the app. Optional; enable with your OpenAI API key.

### AI Image Generate
Generate images from text prompts directly in chat using **OpenAI DALL-E**. Click the image icon in the message toolbar, describe the image you want, and send it to the conversation.

### Share Code Panel
A dedicated panel for sharing code snippets. Click the code icon in the room header to open it. Paste code, optionally select a language, preview it, and share to chat with proper formatting.

### Voice Control Panel
Use the dedicated voice control modal to start/stop listening, monitor wake-word detection state, and type fallback commands when needed.

<p align="center">
  <img src="docs/screenshots/Screenshot%202026-03-24%20111504.png" alt="Voice control modal listening for wake word" width="760" />
</p>

### Video Call Experience
Start room calls with one click, invite teammates via room link, and control mute/video/screen-share directly from the call toolbar.

<p align="center">
  <img src="docs/screenshots/Screenshot%202026-03-24%20111548.png" alt="Video call screen with call controls and connection status" width="900" />
</p>

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
| `GOOGLE_OAUTH_CLIENT_ID` | — | Google OAuth client ID for backend code exchange |
| `GOOGLE_OAUTH_CLIENT_SECRET` | — | Google OAuth client secret for backend code exchange |
| `GITHUB_OAUTH_CLIENT_ID` | — | GitHub OAuth app client ID for backend code exchange |
| `GITHUB_OAUTH_CLIENT_SECRET` | — | GitHub OAuth app client secret for backend code exchange |

Frontend (`frontend/.env`):

| Variable | Description |
|----------|-------------|
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth client ID used by the browser redirect |
| `VITE_GITHUB_CLIENT_ID` | GitHub OAuth app client ID used by the browser redirect |

OAuth callback URLs to register in both providers:

- `http://localhost:5173/oauth/callback/google`
- `http://localhost:5173/oauth/callback/github`

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

---

## Project Structure

```
sean/
├── backend/
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
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
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
└── README.md
```

---

## API Reference

Base URL: `http://localhost:8001/api` (or your backend host)

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register/` | Register a new user |
| `POST` | `/api/auth/login/` | Login; returns JWT access and refresh tokens |
| `POST` | `/api/auth/oauth/google/` | Sign in/up with Google OAuth (returns JWT access/refresh + user) |
| `POST` | `/api/auth/oauth/github/` | Sign in/up with GitHub OAuth (returns JWT access/refresh + user) |
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
