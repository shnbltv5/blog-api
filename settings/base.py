from datetime import timedelta
from pathlib import Path

from django.urls import reverse, reverse_lazy

from settings import conf

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = conf.SECRET_KEY

DJANGO_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = ['rest_framework', 'rest_framework_simplejwt']
LOCAL_APPS = ['apps.auths', 'apps.blog']
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'settings.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'settings.wsgi.application'
ASGI_APPLICATION = 'settings.asgi.application'

AUTH_USER_MODEL = 'auths.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticatedOrReadOnly',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=conf.ACCESS_TOKEN_LIFETIME_MIN),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=conf.REFRESH_TOKEN_LIFETIME_DAYS),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ADMIN_POSTS_CHANGELIST = 'admin:blog_post_changelist'
GITHUB_REPO_URL = 'https://github.com/shnbltv5/blog-api'
UNFOLD_DOCS_URL = 'https://unfoldadmin.com/docs/'

UNFOLD = {
    'SITE_TITLE': 'Blog API admin',
    'SITE_HEADER': 'Blog API',
    'SITE_SUBHEADER': 'Posts, comments & users',
    'SITE_SYMBOL': 'edit_note',
    'ENVIRONMENT': 'apps.blog.callbacks.environment_callback',
    'DASHBOARD_CALLBACK': 'apps.blog.callbacks.dashboard_callback',  # step 9
    'SITE_DROPDOWN': [
        {'icon': 'code', 'title': 'GitHub repository', 'link': GITHUB_REPO_URL},
        {'icon': 'menu_book', 'title': 'Unfold docs', 'link': UNFOLD_DOCS_URL},
    ],
    'COMMAND': {
        'search_models': True,  # Ctrl+K searches model data (needs search_fields)
        'show_history': True,
    },
    'COLORS': {
        'primary': {  # Tailwind teal
            '50': 'oklch(98.4% 0.014 180.72)',
            '100': 'oklch(95.3% 0.051 180.801)',
            '200': 'oklch(91% 0.096 180.426)',
            '300': 'oklch(85.5% 0.138 181.071)',
            '400': 'oklch(77.7% 0.152 181.912)',
            '500': 'oklch(70.4% 0.14 182.503)',
            '600': 'oklch(60% 0.118 184.704)',
            '700': 'oklch(51.1% 0.096 186.391)',
            '800': 'oklch(43.7% 0.078 188.216)',
            '900': 'oklch(38.6% 0.063 188.416)',
            '950': 'oklch(27.7% 0.046 192.524)',
        },
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'Overview',
                'items': [
                    {
                        'title': 'Dashboard',
                        'icon': 'dashboard',
                        'link': reverse_lazy('admin:index'),
                    },
                ],
            },
            {
                'title': 'Content',
                'separator': True,
                'items': [
                    {
                        'title': 'Posts',
                        'icon': 'article',
                        'link': reverse_lazy(ADMIN_POSTS_CHANGELIST),
                        'badge': 'apps.blog.callbacks.drafts_badge',
                        'badge_variant': 'warning',
                    },
                    {
                        'title': 'Comments',
                        'icon': 'chat',
                        'link': reverse_lazy('admin:blog_comment_changelist'),
                    },
                    {
                        'title': 'Categories',
                        'icon': 'folder',
                        'link': reverse_lazy('admin:blog_category_changelist'),
                    },
                    {
                        'title': 'Tags',
                        'icon': 'sell',
                        'link': reverse_lazy('admin:blog_tag_changelist'),
                    },
                ],
            },
            {
                'title': 'Users & Access',
                'separator': True,
                'items': [
                    {
                        'title': 'Users',
                        'icon': 'person',
                        'link': reverse_lazy('admin:auths_user_changelist'),
                        'permission': lambda request: request.user.is_superuser,
                    },
                    {
                        'title': 'Groups',
                        'icon': 'group',
                        'link': reverse_lazy('admin:auth_group_changelist'),
                        'permission': lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },
    'TABS': [
        {
            'models': ['blog.post'],
            'items': [
                {'title': 'All', 'link': reverse_lazy(ADMIN_POSTS_CHANGELIST)},
                {
                    'title': 'Published',
                    'link': lambda request: (
                        reverse(ADMIN_POSTS_CHANGELIST) + '?status__exact=published'
                    ),
                },
                {
                    'title': 'Drafts',
                    'link': lambda request: (
                        reverse(ADMIN_POSTS_CHANGELIST) + '?status__exact=draft'
                    ),
                },
            ],
        },
    ],
}
