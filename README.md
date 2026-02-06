<div align="center">

# Trutim

<img src="frontend/public/trutim.svg" alt="Trutim Logo" width="180" height="180">

### *Where engineers collaborate in real time—no more "did you get my message?"*

**A full-stack real-time collaboration platform** built for developers who value instant communication. Trutim combines live messaging, WebRTC video conferencing, screen sharing, and an AI assistant—all powered by Django Channels and modern React.

<p>
  <img src="docs/assets/coding-robot.svg" alt="Built for developers" width="70" height="70">
  <img src="docs/assets/realtime-rocket.svg" alt="Real-time speed" width="70" height="70">
  <img src="docs/assets/chat-lightning.svg" alt="Lightning chat" width="70" height="70">
  <img src="docs/assets/video-call.svg" alt="Video calls" width="70" height="70">
  <img src="docs/assets/ai-brain.svg" alt="AI assistant" width="70" height="70">
</p>

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
git clone <repository-url>
cd sean
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
| `OPENAI_API_KEY` | — | OpenAI API key for the AI Assistant panel (optional) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use (e.g. `gpt-4o`, `gpt-4o-mini`) |

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
| `POST` | `/api/auth/refresh/` | Refresh access token |

### Protected Endpoints (require `Authorization: Bearer <token>`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rooms/` | List rooms |
| `POST` | `/api/rooms/` | Create a room |
| `GET` | `/api/messages/?room=<id>` | List messages for a room |
| `GET` | `/api/users/` | List users (ViewSet) |
| `POST` | `/api/ai/chat/` | AI chat (streaming; requires `OPENAI_API_KEY`) |

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
