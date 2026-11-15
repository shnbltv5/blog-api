"""Practice Work #3: 50 ORM queries. One function per query, QUERIES maps number -> function."""
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    CharField,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

NEWEST_POSTS_LIMIT = 5
PAGE_SIZE = 10
FIRST_PAGE = 1
EDIT_THRESHOLD = timedelta(hours=1)
UNCATEGORIZED = "Uncategorized"
AVERAGE_PRECISION = 2
TOP_AUTHORS_LIMIT = 5
FULL_NAME_SEPARATOR = " "
HOT_MIN_COMMENTS = 10
NORMAL_MIN_COMMENTS = 3
POPULARITY_HOT = "hot"
POPULARITY_NORMAL = "normal"
POPULARITY_QUIET = "quiet"
FEED_LIMIT = 50
NEWEST_WITH_TAGS_LIMIT = 20
FEED_SEPARATOR = " | "
TAGS_SEPARATOR = ", "


# ---------- Level 1: first queries ----------
def categories_by_name() -> QuerySet[Category]:
    """1. All categories, A -> Z."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """2. Published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")


def newest_published_posts() -> QuerySet[Post]:
    """3. The 5 newest published posts (slice = LIMIT)."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """4. Post with this slug or None (first() never raises)."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """5. Active non-staff users, counted by the database."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """6. True if at least one draft exists (SELECT 1 ... LIMIT 1)."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """7. One page of published posts: LIMIT 10 OFFSET (page - 1) * 10."""
    start: int = (max(page, FIRST_PAGE) - FIRST_PAGE) * PAGE_SIZE
    return published_posts()[start : start + PAGE_SIZE]


# ---------- Level 2: field lookups ----------
def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """8. Title contains word, any letter case."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """9. Email ends with @domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """10. Posts with category = NULL."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """11. Categories whose slug is in the list (SQL IN)."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """12. Posts created in this month of this year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """13. Posts created in the last `days` days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """14. Posts from start to end, both days included (compare the date part only)."""
    return Post.objects.filter(created_at__date__gte=start, created_at__date__lte=end)


# ---------- Level 3: across relations ----------
def author_published_posts(email: str) -> QuerySet[Post]:
    """15. Published posts of the author with this email (any letter case)."""
    return Post.objects.filter(author__email__iexact=email, status=Post.Status.PUBLISHED)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """16. Posts that have this tag."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """17. Comments on posts of this category (comment -> post -> category)."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """18. Users with a published post; distinct() removes JOIN duplicates."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """19. Posts without any tag (LEFT JOIN ... IS NULL)."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """20. Users who never wrote a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """21. Posts with BOTH tags: two filter() calls = two separate JOINs."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)


# ---------- Level 4: Q and F ----------
def search_posts(text: str) -> QuerySet[Post]:
    """22. Text in the title OR in the body."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """23. Published posts without a category OR without tags, each once."""
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """24. Edited more than 1 hour after creation (field vs field with F)."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDIT_THRESHOLD)


def comments_by_post_author() -> QuerySet[Comment]:
    """25. Comments written by the author of the post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """26. Comments older than their post. Must be empty."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


# ---------- Level 5: values / values_list ----------
def published_authors_emails() -> list[str]:
    """27. Unique emails of authors with published posts, A -> Z."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .order_by("author__email")
        .values_list("author__email", flat=True)
        .distinct()
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """28. title, author_email, category_name ('Uncategorized' when NULL)."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .order_by("-created_at")
        .values(
            "title",
            author_email=F("author__email"),
            category_name=Coalesce(F("category__name"), Value(UNCATEGORIZED)),
        )
    )


# ---------- Level 6: aggregate ----------
def posts_stats() -> dict[str, Any]:
    """29. Five numbers in ONE SQL query."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """30. Average comments per published post: annotate per post, then Avg over them."""
    result: dict[str, float] = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comments"))
        .aggregate(average=Avg("comment_count", default=0.0))
    )
    return round(float(result["average"]), AVERAGE_PRECISION)


# ---------- Level 7: annotate ----------
def categories_with_post_count() -> QuerySet[Category]:
    """31. post_count per category, most first, then by name."""
    return Category.objects.annotate(post_count=Count("posts")).order_by("-post_count", "name")


def categories_with_published_count() -> QuerySet[Category]:
    """32. Count with filter= keeps categories with 0 published posts."""
    return Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "name")


def top_authors() -> QuerySet[User]:
    """33. Top 5 users by published posts."""
    return User.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """34. Tags used in at least min_posts posts (filter after annotate = HAVING)."""
    return (
        Tag.objects.annotate(post_count=Count("posts"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )


def posts_per_status() -> list[dict[str, Any]]:
    """35. values() before annotate() = GROUP BY status."""
    return list(Post.objects.values("status").annotate(count=Count("id")).order_by("status"))


def users_activity() -> QuerySet[User]:
    """36. distinct=True stops two JOINs from multiplying each other."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    ).order_by("email")


# ---------- Level 8: database functions and conditions ----------
def search_users_by_full_name(text: str) -> QuerySet[User]:
    """37. Build 'First Last' in SQL, then search in it."""
    return User.objects.annotate(
        full_name=Concat(
            "first_name", Value(FULL_NAME_SEPARATOR), "last_name", output_field=CharField()
        )
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """38. Published posts per month, oldest first."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """39. comment_count + popularity: hot (>=10), normal (>=3), quiet."""
    return (
        Post.objects.annotate(comment_count=Count("comments"))
        .annotate(
            popularity=Case(
                When(comment_count__gte=HOT_MIN_COMMENTS, then=Value(POPULARITY_HOT)),
                When(comment_count__gte=NORMAL_MIN_COMMENTS, then=Value(POPULARITY_NORMAL)),
                default=Value(POPULARITY_QUIET),
                output_field=CharField(),
            )
        )
        .order_by("-comment_count")
    )


# ---------- Level 9: changing data ----------
def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """40. Search by the unique slug, so 'Django ORM' and 'django orm' are one tag."""
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """41. One UPDATE; update() skips auto_now, so updated_at is set by hand."""
    now = timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT, created_at__lt=now - timedelta(days=days)
    ).update(status=Post.Status.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """42. add() skips posts that already have the tag."""
    tag: Tag = Tag.objects.get(slug=tag_slug)
    post_ids: list[int] = list(
        Post.objects.filter(category__slug=category_slug).values_list("id", flat=True)
    )
    tag.posts.add(*post_ids)
    return len(post_ids)


def merge_categories(source_slug: str, target_slug: str) -> int:
    """43. Move posts first (SET_NULL would drop them), then delete the source."""
    if source_slug == target_slug:
        raise ValueError("Source and target categories must be different.")
    target: Category = Category.objects.get(slug=target_slug)
    with transaction.atomic():
        moved: int = Post.objects.filter(category__slug=source_slug).update(category=target)
        Category.objects.filter(slug=source_slug).delete()
    return moved


def delete_inactive_users_comments() -> int:
    """44. delete() returns (total, per_model); we need the total."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


# ---------- Level 10: select_related / prefetch_related ----------
def published_feed() -> list[str]:
    """45. 'title | email | category' for 50 posts, exactly 1 query (JOIN)."""
    posts = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author", "category")
        .order_by("-created_at")[:FEED_LIMIT]
    )
    return [
        FEED_SEPARATOR.join(
            (
                post.title,
                post.author.email,
                post.category.name if post.category else UNCATEGORIZED,
            )
        )
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """46. 'title: tag1, tag2' for 20 posts, at most 2 queries."""
    posts = Post.objects.prefetch_related(
        Prefetch("tags", queryset=Tag.objects.order_by("name"))
    ).order_by("-created_at")[:NEWEST_WITH_TAGS_LIMIT]
    return [
        f"{post.title}: {TAGS_SEPARATOR.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    """47. Filter INSIDE the prefetch, so no extra query per category."""
    published = Post.objects.filter(status=Post.Status.PUBLISHED).order_by("-created_at")
    categories = Category.objects.prefetch_related(
        Prefetch("posts", queryset=published, to_attr="published_posts")
    ).order_by("name")
    return {
        category.name: [post.title for post in category.published_posts]
        for category in categories
    }


# ---------- Level 11: Subquery / Exists ----------
def posts_with_last_comment() -> QuerySet[Post]:
    """48. Body of the newest comment of each published post (one column, one row)."""
    newest_comment = (
        Comment.objects.filter(post=OuterRef("pk")).order_by("-created_at").values("body")[:1]
    )
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(last_comment=Subquery(newest_comment))
        .order_by("-created_at")
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    """49. EXISTS instead of JOIN + distinct()."""
    staff_comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """50. Status of each user's newest post via a subquery, then filter by it."""
    latest_status = (
        Post.objects.filter(author=OuterRef("pk")).order_by("-created_at").values("status")[:1]
    )
    return User.objects.annotate(latest_post_status=Subquery(latest_status)).filter(
        latest_post_status=Post.Status.DRAFT
    )


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
