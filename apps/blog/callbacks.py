import json
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest

from apps.blog.models import Category, Comment, Post
from settings.conf import BLOG_ENV_ID

PROD_ENV_ID = 'prod'
TOP_AUTHORS_LIMIT = 5
PERCENT = 100
CHART_COLOR = 'var(--color-primary-600)'


def environment_callback(request: HttpRequest) -> list[str]:
    """Badge in the header: text + color (info / danger / warning / success)."""
    if BLOG_ENV_ID == PROD_ENV_ID:
        return ['Production', 'danger']  # red
    return ['Local', 'warning']  # orange


def drafts_badge(request: HttpRequest) -> int:
    """Number of drafts next to 'Posts' in the sidebar."""
    return Post.objects.filter(status=Post.Status.DRAFT).count()


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Data for templates/admin/index.html. Everything is counted in the database."""
    user_model = get_user_model()

    # 1 query: both counters at once (conditional aggregation)
    post_counts: dict[str, int] = Post.objects.aggregate(
        published=Count('id', filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count('id', filter=Q(status=Post.Status.DRAFT)),
    )
    published: int = post_counts['published']
    drafts: int = post_counts['drafts']
    total_posts: int = published + drafts

    # bar chart: posts per category (1 query with GROUP BY)
    categories = Category.objects.annotate(total=Count('posts')).order_by('-total')
    chart: dict[str, Any] = {
        'labels': [category.name for category in categories],
        'datasets': [
            {
                'label': 'Posts',
                'data': [category.total for category in categories],
                'backgroundColor': CHART_COLOR,
            },
        ],
    }

    # table: top authors
    top_authors = user_model.objects.annotate(total=Count('posts')).order_by('-total')[
        :TOP_AUTHORS_LIMIT
    ]
    table: dict[str, Any] = {
        'headers': ['Author', 'Email', 'Posts'],
        'rows': [
            [f'{author.first_name} {author.last_name}', author.email, author.total]
            for author in top_authors
        ],
    }

    published_percent: int = round(published * PERCENT / total_posts) if total_posts else 0
    draft_percent: int = PERCENT - published_percent if total_posts else 0

    context.update(
        {
            'cards': [
                {'title': 'Users', 'icon': 'person', 'value': user_model.objects.count()},
                {'title': 'Published posts', 'icon': 'article', 'value': published},
                {'title': 'Drafts', 'icon': 'edit_note', 'value': drafts},
                {'title': 'Comments', 'icon': 'chat', 'value': Comment.objects.count()},
            ],
            'posts_chart': json.dumps(chart),  # Chart.js expects a JSON string
            'top_authors': table,
            'published_percent': published_percent,
            'draft_percent': draft_percent,
            'published_label': f'{published_percent}%',
            'draft_label': f'{draft_percent}%',
        }
    )
    return context
