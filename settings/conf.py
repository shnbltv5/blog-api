from decouple import Csv, config

BLOG_ENV_ID: str = config('BLOG_ENV_ID',default='local')

SECRET_KEY: str = config('BLOG_SECRET_KEY')
DEBUG: bool = config('BLOG_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS: list[str] = config('BLOG_ALLOWED_HOSTS', default='', cast=Csv())

DB_NAME: str = config('BLOG_DB_NAME', default='blog_api')
DB_USER: str = config('BLOG_DB_USER', default='blog_api')
DB_PASSWORD: str = config('BLOG_DB_PASSWORD', default='')
DB_HOST: str = config('BLOG_DB_HOST', default='localhost')
DB_PORT: str = config('BLOG_DB_PORT', default='5432')

ACCESS_TOKEN_LIFETIME_MIN: int = config('BLOG_ACCESS_TOKEN_LIFETIME_MIN', default=15, cast=int)
REFRESH_TOKEN_LIFETIME_DAYS: int = config('BLOG_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
