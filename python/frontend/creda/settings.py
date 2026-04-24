"""
Django CREDA Frontend — settings.

Separate database (creda_django) for Django-managed tables (User, sessions, admin).
FastAPI owns domain tables in creda_api database via Alembic.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from python/ root
_env_path = BASE_DIR.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Ngrok / tunnel support: trust HTTPS behind reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF: trust ngrok origins (populated from env)
_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()] if _csrf_origins else []

# ── Apps ───────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # CREDA apps
    "accounts",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "creda.middleware.async_user_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "creda.middleware.backend_client_middleware",
]

ROOT_URLCONF = "creda.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "creda.asgi.application"
WSGI_APPLICATION = "creda.wsgi.application"

# ── Database (Django tables only — User, sessions, admin) ─────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DJANGO_DB_NAME", "creda_django"),
        "USER": os.environ.get("DJANGO_DB_USER", "creda_admin"),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "creda_secure_2025"),
        "HOST": os.environ.get("DJANGO_DB_HOST", "localhost"),
        "PORT": os.environ.get("DJANGO_DB_PORT", "8010"),
    }
}

# ── Auth ───────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── FastAPI Backend ────────────────────────────────────────
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8001")
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")

# ── Static ─────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Internationalization ───────────────────────────────────
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("hi", "हिन्दी"),
    ("ta", "தமிழ்"),
    ("te", "తెలుగు"),
    ("mr", "मराठी"),
    ("bn", "বাংলা"),
    ("kn", "ಕನ್ನಡ"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Sessions ───────────────────────────────────────────────
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
