from django.http import HttpRequest

from apps.blog.models import Post
from settings.conf import BLOG_ENV_ID

PROD_ENV_ID = "prod"


def environment_callback(request: HttpRequest) -> list[str]:
    """Badge in the header: text + color (info / danger / warning / success)."""
    if BLOG_ENV_ID == PROD_ENV_ID:
        return ["Production", "danger"]   # red
    return ["Local", "warning"]            # orange


def drafts_badge(request: HttpRequest) -> int:
    """Number of drafts next to 'Posts' in the sidebar."""
    return Post.objects.filter(status=Post.Status.DRAFT).count()
