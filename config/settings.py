from pathlib import Path
from decimal import Decimal
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, True))
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default="dev-only-change-me")
if not DEBUG and (not SECRET_KEY or SECRET_KEY == "dev-only-change-me"):
    raise ImproperlyConfigured("SECRET_KEY must be set to a unique production secret when DEBUG=False.")
render_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="")
default_allowed_hosts = ["127.0.0.1", "localhost", "testserver"] if DEBUG else ([render_hostname] if render_hostname else [])
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=default_allowed_hosts)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured when DEBUG=False.")
default_csrf_origins = [f"https://{render_hostname}"] if render_hostname else []
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=default_csrf_origins)

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "drf_spectacular", "store", "accounts", "cart", "orders",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True, "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "cart.context_processors.cart_summary",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "store:home"
LOGOUT_REDIRECT_URL = "store:home"
DELIVERY_FEE = env("DELIVERY_FEE", default=Decimal("25.00"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="orders@novamarket.example")
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/hour", "user": "1000/hour", "auth": "5/minute"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "NOVA MARKET API",
    "DESCRIPTION": "Versioned REST API for catalogue, accounts, carts, and orders.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

