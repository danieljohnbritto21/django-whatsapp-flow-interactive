"""
Django settings for whatsapp_project project.
"""

from pathlib import Path
import os

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================
# SECURITY & DEBUG
# =============================================

SECRET_KEY = os.environ.get(
    'SECRET_KEY', 
    'django-insecure-xk=bgz=&omoq)*2#m9fb_@(h+zu0kfum@z(@$x8o5ninb9f61h'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# Load allowed hosts from environment variable for better security.
# Example: ALLOWED_HOSTS="localhost,127.0.0.1,your-ngrok-url.ngrok-free.dev"
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = os.environ.get(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    ).split(",")

# =============================================
# WHATSAPP CONFIGURATION
# =============================================
# SECURITY WARNING: These values should be kept secret and loaded from environment variables.
# Do not commit them to version control.

# WhatsApp Configuration (Local Development Only)

VERIFY_TOKEN = "whatsapp123"

PHONE_NUMBER_ID = "1182726391596293"

WHATSAPP_TOKEN = "EAAWGS1a6teABRyeZCyegcJ7S1I6TyOiFfvLOrVZAoXwCYMzSAgQuEovN932cm1vdLfAsucZC03W4RdPigZAhZApp63ZANYjEAFDZAuxe2At7jV62JJ3tAuRiXrboETY6txdbZASISZCMg3rY5gr6ZCaZCf5ZAZCqQoVtMNg4ZBmYjKzNDNNG2OO1hGIRiJOwBSg8vZCqRPhZA4R4ndvX6Ph3JQKLSC1BXCqE2K20HAcJaggHKI4XMZAKVEqNxwidaroyHN4GJrpHRlL5fvpYlQkl2EVZAooycCzSS3B2KccIPzQHnkUNUZD"

# =============================================
# APPLICATION DEFINITION
# =============================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whatsapp_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'whatsapp_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'whatsapp_project.wsgi.application'

# =============================================
# DATABASE
# =============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =============================================
# PASSWORD VALIDATION
# =============================================
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =============================================
# INTERNATIONALIZATION
# =============================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# =============================================
# STATIC & MEDIA FILES
# =============================================
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================
# THAAGAM FOUNDATION SETTINGS
# =============================================

# WhatsApp Flow IDs
FLOW_ID = "1458360002725146"
FOOD_FLOW_ID = "1719210375883183"

# WhatsApp Header Image ID (optional).
# Prefer uploading the local header image at runtime (see WHATSAPP_HEADER_IMAGE_PATH).
HEADER_IMAGE_ID = os.environ.get("HEADER_IMAGE_ID", "")

# Local header image path used to upload the WhatsApp header media.
WHATSAPP_HEADER_IMAGE_PATH = BASE_DIR / 'media' / 'whatsapp_images' / 'thaagam_logo.png'


# WhatsApp Flow Encryption Private Key
FLOW_PRIVATE_KEY = os.environ.get("FLOW_PRIVATE_KEY")

# Easebuzz Configuration
EASEBUZZ_MERCHANT_KEY = os.environ.get("EASEBUZZ_MERCHANT_KEY")
EASEBUZZ_SALT = os.environ.get("EASEBUZZ_SALT")
EASEBUZZ_ENV = os.environ.get("EASEBUZZ_ENV", 'test')
EASEBUZZ_CALLBACK_URL = os.environ.get("EASEBUZZ_CALLBACK_URL")

# Thaagam Foundation Settings
THAAGAM_LOGO_URL = 'https://www.thaagam.org/media/whatsapp_images/thaagam_logo.png'
THAAGAM_DONATION_URL = 'https://www.thaagam.org/causes-detail/thaali/'

THAAGAM_FOUNDATION = {
    'NAME': 'Thaagam Foundation',
    'WEBSITE': 'https://thaagam.org',
    'EMAIL': 'foundation@thaagam.org',
    'PHONE': '+919876543210',
    'UPI_ID': 'thaagam@upi',
    'BANK_NAME': 'HDFC Bank',
    'BANK_ACCOUNT': '1234567890',
    'BANK_IFSC': 'HDFC0001234',
    'RAZORPAY_KEY': 'rzp_test_xxxxxxxxxx',
    'RAZORPAY_SECRET': 'xxxxxxxxxxxxxxxxxxxxx',
}

# =============================================
# LOGGING CONFIGURATION
# =============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'thaagam_donations.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'whatsapp_app': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}