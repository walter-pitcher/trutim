# Trutim

**Real-time collaboration platform for engineers and developers.** A full-stack application providing live messaging, video conferencing, and screen sharing—built with Django Channels (WebSockets) and WebRTC.

---

## Table of Contents

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

## Features

| Feature | Description |
|---------|-------------|
| **Live Chat** | Real-time messaging via WebSockets with instant delivery |
| **Video Calls** | WebRTC-based peer-to-peer video conferencing |
| **Screen Sharing** | Share your screen during active video calls |
| **Emoji Support** | Quick emoji bar, full emoji picker, and message reactions |
| **User Profiles** | Custom profiles with username, email, and professional title |
| **Room Management** | Create and join chat rooms with persistent message history |

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Django 4.x, Django REST Framework, Django Channels, Daphne |
| **Authentication** | JWT (Simple JWT) |
| **Database** | PostgreSQL (production) / SQLite (development) |
| **Real-time** | WebSockets, WebRTC |
| **Frontend** | React 19, Vite 7 |
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

The project uses SQLite by default for development. No additional configuration needed.

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
│   │   ├── components/       # EmojiPicker, VideoCall
│   │   ├── context/          # AuthContext
│   │   ├── hooks/            # useChatSocket, useCallSocket
│   │   ├── pages/            # Login, Register, Dashboard, Room
│   │   └── api.js            # Axios API client
│   ├── package.json
│   └── vite.config.js
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

---

## WebSocket Endpoints

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
