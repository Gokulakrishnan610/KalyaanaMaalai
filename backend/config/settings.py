"""Project settings. Values that change per machine come from the .env file in the repo root."""
import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


ENVIRONMENT = env("ENVIRONMENT", "dev")
DEBUG = ENVIRONMENT == "dev"
SECRET_KEY = env("SECRET_KEY", "dev-only-secret-change-me-0123456789")
if not DEBUG and SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Set a real SECRET_KEY in .env when ENVIRONMENT is not dev")
ALLOWED_HOSTS = ["*"] if DEBUG else env("ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    # our apps (one folder per part of the business)
    "common",
    "accounts",
    "clients",
    "enquiries",
    "weddings",
    "tasks",
    "vendors",
    "quotations",
    "payments",
    "ai_tools",
    "notifications",
    "dashboard",
    "incidents",
    "live",
    "portal",
    "mailer",
    "agreements",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves the admin's CSS when deployed
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", "postgresql://wedding:wedding@localhost:5432/wedding"), conn_max_age=60
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # everything is stored in UTC; the website shows local time
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
MEDIA_URL = "uploads/"
MEDIA_ROOT = BASE_DIR / env("UPLOAD_DIR", "uploads")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- API ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {"login": "20/min", "public_pay": "60/min", "portal_auth": "20/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "KalyaanaMaalai - Wedding Planning API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("LOGIN_MINUTES", "720")))}

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")
CUSTOMER_SITE_URL = env("CUSTOMER_SITE_URL", "http://localhost:5174")  # the couples' website
CORS_ALLOWED_ORIGINS = [FRONTEND_URL, "http://localhost:5173", CUSTOMER_SITE_URL]
CORS_ALLOW_HEADERS = [*default_headers, "idempotency-key", "last-event-id"]  # lets the website retry a payment safely
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL, CUSTOMER_SITE_URL]

# --- Outside services. While MOCK_EXTERNALS is true they return fake answers, so the demo never breaks.
# tests always use the fake answers, whatever .env says, so they never reach a real service or spend real money
MOCK_EXTERNALS = "test" in sys.argv or env("MOCK_EXTERNALS", "true").lower() == "true"
# the fake payment checkout is dev-only unless this is switched on on purpose (for example for a public demo)
ALLOW_DEMO_PAYMENTS = env("ALLOW_DEMO_PAYMENTS", "false").lower() == "true"
# AI is Groq. It is called for real when a key is set and either MOCK_EXTERNALS is off or AI_LIVE=true, so quotation
# reading can be real while payments, email and Telegram stay fake. Tests never call it.
GROQ_API_KEY = env("GROQ_API_KEY")
GROQ_MODEL = env("GROQ_MODEL")  # text model, empty = openai/gpt-oss-120b
GROQ_VISION_MODEL = env("GROQ_VISION_MODEL")  # reads photos and scanned PDFs, empty = qwen/qwen3.8-27b
AI_LIVE = "test" not in sys.argv and (not MOCK_EXTERNALS or env("AI_LIVE", "false").lower() == "true")
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")
DEFAULT_FROM_EMAIL = env("MAIL_FROM", "Shaandaar Events <no-reply@shaandaar.example>")
EMAIL_HOST = env("SMTP_HOST")
EMAIL_PORT = int(env("SMTP_PORT", "587"))
EMAIL_HOST_USER = env("SMTP_USER")
EMAIL_HOST_PASSWORD = env("SMTP_PASS")
EMAIL_USE_TLS = EMAIL_PORT == 587  # Mailtrap and most providers want STARTTLS on 587
EMAIL_TIMEOUT = 10
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if MOCK_EXTERNALS or not EMAIL_HOST
    else "django.core.mail.backends.smtp.EmailBackend"
)

# --- Live updates and background work (both use Redis) ---
TESTING = "test" in sys.argv
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
LIVE_BACKEND = "memory" if TESTING else "redis"  # tests keep events in memory, so they need no Redis
LIVE_ALERTS = not TESTING  # saved alerts for new quotations and payments (tests turn them on when needed)
CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = TESTING  # in tests, background tasks simply run on the spot
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = "UTC"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
WHITENOISE_USE_FINDERS = DEBUG  # lets the admin look right when the server is started with uvicorn
