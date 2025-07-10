from pathlib import Path
from django.urls import reverse_lazy
import os
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET= os.getenv('STRIPE_WEBHOOK_SECRET')
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = "django-insecure-w0&@r2_2x%j*$jy12&hb_g6qgt%ppkdx**+%!l@gf8v*%91v7z"

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.pythonanywhere.com', 'www.allbikesvespawharehouse.com.au']

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "users.apps.UsersConfig",
    "dashboard.apps.DashboardConfig",
    "inventory.apps.InventoryConfig",
    "service.apps.ServiceConfig",
    "payments.apps.PaymentsConfig",
    "mailer.apps.MailerConfig",
    'import_export',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "SCOOTER_SHOP.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                'dashboard.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = "SCOOTER_SHOP.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = 'Australia/Perth'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = 'users.User'

LOGIN_REDIRECT_URL = reverse_lazy('core:index')
LOGOUT_REDIRECT_URL = reverse_lazy('core:index')
SITE_BASE_URL = 'http://localhost:8000'

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')


SESSION_COOKIE_AGE = 10000
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

STRIPE_PUBLISHABLE_KEY = "pk_test_51RRCzbPH0oVkn2F1ZCB43p08cHzPiROnrVDvRbggNjvm4WAsDHhNy8gzd00qhxCItqk5Y8yhtRi9BJSIlt8dr8x100D0oG7sKC"


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

DEFAULT_FROM_EMAIL = 'ethan.betts.dev@gmail.com'
LOGIN_URL = 'users:login'
ADMIN_EMAIL = 'ethan.betts.dev@gmail.com'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ethan.betts.dev@gmail.com'
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")


MECHANICDESK_BOOKING_TOKEN = os.getenv('MECHANICDESK_BOOKING_TOKEN')
