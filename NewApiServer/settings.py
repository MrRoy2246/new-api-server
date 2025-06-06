import os
from pathlib import Path

import storages.backends.s3boto3
from dotenv import load_dotenv
load_dotenv(dotenv_path = r'C:\ABIN-Work\NewApiServer\NewApiServer\.env')
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-sjty_3a^5xukhny$qni2=$p1e@at%mw-&e%ime^x@9*f$w28@8'


# MEDIA_DIR = BASE_DIR / 'media'
STATIC_DIR = BASE_DIR / 'static'

DEBUG = True
ALLOWED_HOSTS = []
# Application definition

# accceleye setting-------->

# Fetch ALLOWED_HOSTS from environment variable or default to '*'
allowed_hosts_env = os.getenv('ALLOWED_HOSTS')
ALLOWED_HOSTS = allowed_hosts_env.split(',') if allowed_hosts_env else ['*']

# Fetch CORS_ALLOW_ALL_ORIGINS from environment variable or default to True
cors_allow_all_origins_env = os.getenv('CORS_ALLOW_ALL_ORIGINS')
CORS_ALLOW_ALL_ORIGINS = True if cors_allow_all_origins_env is None else cors_allow_all_origins_env == 'True'

# Fetch CSRF_TRUSTED_ORIGINS from environment variable or default to allowing all domains
csrf_trusted_origins_env = os.getenv('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = csrf_trusted_origins_env.split(',') if csrf_trusted_origins_env else ['http://*', 'https://*']

print(f"Allowed hosts: {ALLOWED_HOSTS} and CSRF origins: {CSRF_TRUSTED_ORIGINS}")

INSTALLED_APPS = [
    'storages',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',
    'rest_framework',
    'django_seed',
    'channels',
    
    
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

ROOT_URLCONF = 'NewApiServer.urls'

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

WSGI_APPLICATION = 'NewApiServer.wsgi.application'
ASGI_APPLICATION = 'NewApiServer.asgi.application'


# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'elasticsearch': {
#             'level': 'INFO',
#             'class': 'myapp.loging_config.ElasticsearchHandler',
#         },
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console', 'elasticsearch'],
#         'level': 'INFO',
#     },
# }



# Use in-memory channel layer for development (or Redis for production)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',  # Use Redis backend in production
#     },
# }


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
            # 'capacity': 15000,
            # 'expiry': 100,
            # 'group_expiry': 86400, 
        },
    },
}

# CELERY_BROKER_URL = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# CELERY_TASK_ACKS_LATE = True  # Allow workers to prefetch tasks
# CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Reduce prefetching to avoid queue starvation
# CELERY_TASK_TRACK_STARTED = True  # Track task start time for monitoring
# CELERY_BROKER_TRANSPORT_OPTIONS = {
#     'visibility_timeout': 3600,  # 1 hour for long-running tasks
#     'fanout_prefix': True,  # Optimize Redis pub/sub
#     'fanout_patterns': True,
# }
# CELERY_RESULT_EXTENDED = True

# CELERY_BEAT_SCHEDULE = {
#     'cleanup-task': {
#         'task': 'camera.tasks.cleanup_no_weapon_images',
#         'schedule': 60.0, 
#         'options': {'queue': 'celery_beat'},
#     },
# }

# MAX_MESSAGE_LENGTH = 200 * 1024 * 1024
# ASGI_THREADS = 100





# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3new',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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

# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': (
#         'rest_framework_simplejwt.authentication.JWTAuthentication',
#     ),
# }


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "Accelx@123456")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "abin-roy")  

AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", "https://minioodb.accelx.net")
AWS_QUERYSTRING_AUTH = False
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_VERIFY = os.getenv("AWS_S3_VERIFY", "True") == "True"


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'
print(MEDIA_URL)





print("🧪 Using storage backend:", DEFAULT_FILE_STORAGE)

# import boto3
# from botocore.exceptions import ClientError

# session = boto3.session.Session()

# s3 = session.client(
#     service_name='s3',
#     endpoint_url='http://192.168.1.150:9000',
#     aws_access_key_id='acceleye_api',
#     aws_secret_access_key='Accelx@123456',
# )

# try:
#     response = s3.list_buckets()
#     print("✅ MinIO Connected! Buckets:")
#     for bucket in response['Buckets']:
#         print(f" - {bucket['Name']}")
# except ClientError as e:
#     print("❌ Failed to connect to MinIO:", e)

# print("✅ MinIO Config Loaded:", AWS_S3_ENDPOINT_URL, AWS_STORAGE_BUCKET_NAME)



# import boto3
# from botocore.client import Config

# s3 = boto3.client('s3',
#     endpoint_url='https://minioodb.accelx.net',
#     aws_access_key_id='acceleye_api',
#     aws_secret_access_key='Accelx@123456',
#     config=Config(signature_version='s3v4'),
#     verify=False  # only if self-signed cert
# )

# response = s3.list_objects_v2(Bucket='abinroy')
# print(response)