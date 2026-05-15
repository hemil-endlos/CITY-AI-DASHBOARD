# CITY-AI Dashboard

Django + Django REST Framework + **Channels** for live updates. Ingest API for images from **CITY-AI Detection**. This project uses **its own** Python virtual environment — **do not** install PyTorch, Ultralytics, or OpenCV here.

## Prerequisites

- Python 3.10+ recommended  
- Optional: **Redis** if you set `USE_REDIS_CHANNEL_LAYER=1` (see `.env.example`)

## Layout

| Path | Purpose |
|------|---------|
| `manage.py` | Django entrypoint |
| `surveillance/` | Project settings, URLs, ASGI |
| `detections/` | Models, REST API, WebSocket consumer, templates |
| `media/` | Uploaded detection images (created at runtime) |

## Setup (isolated `.venv`)

From **this directory** (`CITY-AI Dashboard`):

### 1. Create and activate the virtual environment

**PowerShell**

```powershell
cd "CITY-AI Dashboard"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**cmd**

```bat
cd "CITY-AI Dashboard"
py -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Installs: Django, DRF, Channels, Daphne, channels-redis, Pillow, python-dotenv. **No Ultralytics / torch / OpenCV.**

### 3. Configure environment

```powershell
copy .env.example .env
```

Edit **`.env`**:

- **`DJANGO_SECRET_KEY`** — use a long random string in production  
- **`DJANGO_DEBUG`** — `1` for dev, `0` for production  
- **`DJANGO_ALLOWED_HOSTS`** — comma-separated hosts  
- **`USE_REDIS_CHANNEL_LAYER`** — `0` = in-memory Channels (dev); `1` = Redis (`REDIS_URL`)

### 4. Database migrations

```powershell
python manage.py migrate
```

### 5. Create an admin user

```powershell
python manage.py createsuperuser
```

### 6. Run the development server

**HTTP + admin (WS may be limited under `runserver`):**

```powershell
python manage.py runserver 8000
```

**Full ASGI (recommended if WebSockets misbehave under `runserver`):**

```powershell
daphne -b 127.0.0.1 -p 8000 surveillance.asgi:application
```

- Dashboard: `http://127.0.0.1:8000/`  
- API: `POST http://127.0.0.1:8000/api/detections/` (multipart `image` + metadata)

## CITY-AI Detection

Point the Detection service **`DJANGO_BASE_URL`** (in the *other* project’s `.env`) to this server, e.g. `http://127.0.0.1:8000`.

No paths here assume a shared root-level virtual environment.
