"""Project settings. Values that change per machine come from the .env file in the repo root."""
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
    "DEFAULT_THROTTLE_RATES": {"login": "20/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "KalyaanaMaalai - Wedding Planning API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("LOGIN_MINUTES", "720")))}

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:5173")
CORS_ALLOWED_ORIGINS = [FRONTEND_URL, "http://localhost:5173"]

# --- Outside services. While MOCK_EXTERNALS is true they return fake answers, so the demo never breaks.
MOCK_EXTERNALS = env("MOCK_EXTERNALS", "true").lower() == "true"
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL")
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")
EMAIL_HOST = env("SMTP_HOST")
EMAIL_PORT = int(env("SMTP_PORT", "587"))
EMAIL_HOST_USER = env("SMTP_USER")
EMAIL_HOST_PASSWORD = env("SMTP_PASS")
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if MOCK_EXTERNALS or not EMAIL_HOST
    else "django.core.mail.backends.smtp.EmailBackend"
)
