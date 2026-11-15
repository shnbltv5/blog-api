import random
import time
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

# --- defaults ---
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

# --- users ---
SEED_PASSWORD = "seedpass123"
EMAIL_DOMAIN = "example.com"
INACTIVE_RATIO = 0.1
STAFF_RATIO = 0.05
FIRST_EMAIL_SUFFIX = 2

# --- posts ---
PUBLISHED_RATIO = 0.7
NO_CATEGORY_RATIO = 0.1
MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
MIN_PARAGRAPHS = 3
MAX_PARAGRAPHS = 6
TITLE_WORDS = 6
SLUG_SUFFIX_RESERVE = 6  # place for "-12345"
FIRST_SLUG_SUFFIX = 2

# --- dates ---
DATE_RANGE_DAYS = 365 # posts are spread over the last year
EDITED_RATIO = 0.3 # share of posts edited after creation
MIN_EDIT_DELAY_DAYS = 1
MAX_EDIT_DELAY_DAYS = 30

# --- comments ---
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

# --- output ---
LABEL_WIDTH = 12
NUMBER_WIDTH = 5

CATEGORY_NAMES: tuple[str, ...] = (
    "Python", "Django", "DevOps", "Databases",
    "Frontend", "Machine Learning", "Security", "Career",
)
TAG_NAMES: tuple[str, ...] = (
    "Python", "Django", "DRF", "PostgreSQL", "Redis",
    "Celery", "Docker", "Kubernetes", "Linux", "Git",
    "Testing", "Async", "REST API", "ORM", "Performance",
    "JavaScript", "React", "CI/CD", "Nginx", "Tutorial",
)


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users", type=int, default=DEFAULT_USERS, help="Number of users to create"
        )
        parser.add_argument(
            "--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create"
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Delete existing data before seeding"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        self._validate_counts(users=users_count, posts=posts_count, comments=comments_count)
        self.fake = Faker()
        self.now: datetime = timezone.now()  # one "now" for all dates of this run
        started: float = time.perf_counter()

        with transaction.atomic():  # all or nothing + much faster on SQLite
            if clear:
                self._clear()
            users = self._create_users(users_count)
            categories = self._create_named(Category, CATEGORY_NAMES)
            tags = self._create_named(Tag, TAG_NAMES)
            posts = self._create_posts(posts_count)
            comments = self._create_comments(comments_count, posts)

        elapsed: float = time.perf_counter() - started
        rows: tuple[tuple[str, int], ...] = (
            ("Users", len(users)),
            ("Categories", len(categories)),
            ("Tags", len(tags)),
            ("Posts", len(posts)),
            ("Comments", len(comments)),
        )
        for label, number in rows:
            self.stdout.write(f"{label + ':':<{LABEL_WIDTH}}{number:>{NUMBER_WIDTH}} created")
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.2f} seconds"))

    # ---------- checks ----------
    def _validate_counts(self, **counts: int) -> None:
        for name, value in counts.items():
            if value < 0:
                raise CommandError(f"--{name} must be 0 or greater, got {value}.")

    # ---------- clear ----------
    def _clear(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING("Old data deleted (superusers kept)."))

    # ---------- dates ----------
    def _random_moment_between(self, start: datetime, end: datetime) -> datetime:
        """Random datetime from start to end (both included)."""
        seconds: int = max(int((end - start).total_seconds()), 0)
        return start + timedelta(seconds=random.randint(0, seconds))

    def _post_dates(self) -> tuple[datetime, datetime]:
        """created_at in the last year; ~30% of posts edited 1-30 days later (not after now)."""
        year_ago: datetime = self.now - timedelta(days=DATE_RANGE_DAYS)
        created_at: datetime = self._random_moment_between(year_ago, self.now)
        if random.random() >= EDITED_RATIO:
            return created_at, created_at  # not edited: updated_at == created_at
        delay = timedelta(days=random.randint(MIN_EDIT_DELAY_DAYS, MAX_EDIT_DELAY_DAYS))
        return created_at, min(created_at + delay, self.now)

    # ---------- users ----------
    def _unique_email(self, first_name: str, last_name: str, used: set[str]) -> str:
        local: str = f"{slugify(first_name)}.{slugify(last_name)}"
        email: str = f"{local}@{EMAIL_DOMAIN}"
        suffix: int = FIRST_EMAIL_SUFFIX
        while email in used:
            email = f"{local}{suffix}@{EMAIL_DOMAIN}"
            suffix += 1
        used.add(email)
        return email

    def _create_users(self, count: int) -> list[User]:
        if count == 0:
            return []
        used_emails: set[str] = set(User.objects.values_list("email", flat=True))  # 1 query
        password_hash: str = make_password(SEED_PASSWORD)  # hash ONCE
        users: list[User] = []
        for _ in range(count):
            first_name: str = self.fake.first_name()
            last_name: str = self.fake.last_name()
            users.append(
                User(
                    email=self._unique_email(first_name, last_name, used_emails),
                    first_name=first_name,
                    last_name=last_name,
                    password=password_hash,
                    is_active=random.random() >= INACTIVE_RATIO,
                    is_staff=random.random() < STAFF_RATIO,
                )
            )
        return User.objects.bulk_create(users)

    # ---------- categories / tags ----------
    def _create_named(
        self, model: type[Category] | type[Tag], names: tuple[str, ...]
    ) -> list[Category] | list[Tag]:
        existing: set[str] = set(model.objects.values_list("slug", flat=True))
        new_objects = [
            model(name=name, slug=slugify(name))
            for name in names
            if slugify(name) not in existing
        ]
        return model.objects.bulk_create(new_objects)

    # ---------- posts ----------
    def _unique_slug(self, title: str, used: set[str], max_length: int) -> str:
        base: str = slugify(title)[: max_length - SLUG_SUFFIX_RESERVE].strip("-")
        slug: str = base
        suffix: int = FIRST_SLUG_SUFFIX
        while slug in used:
            slug = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        return slug

    def _random_status(self) -> str:
        if random.random() < PUBLISHED_RATIO:
            return Post.Status.PUBLISHED
        return Post.Status.DRAFT

    def _random_body(self) -> str:
        paragraphs_count: int = random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS)
        return "\n\n".join(self.fake.paragraphs(nb=paragraphs_count))

    def _create_posts(self, count: int) -> list[Post]:
        if count == 0:
            return []
        author_ids: list[int] = list(User.objects.values_list("id", flat=True))
        if not author_ids:
            raise CommandError("Cannot create posts: there are no users. Use --users N.")
        category_ids: list[int] = list(Category.objects.values_list("id", flat=True))
        tags: list[Tag] = list(Tag.objects.all())
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))
        slug_max_length: int = Post._meta.get_field("slug").max_length

        posts: list[Post] = []
        for _ in range(count):
            title: str = self.fake.sentence(nb_words=TITLE_WORDS).rstrip(".")
            no_category: bool = not category_ids or random.random() < NO_CATEGORY_RATIO
            # bulk_create skips save(), so the slug is set here
            posts.append(
                Post(
                    author_id=random.choice(author_ids),
                    title=title,
                    slug=self._unique_slug(title, used_slugs, slug_max_length),
                    body=self._random_body(),
                    category_id=None if no_category else random.choice(category_ids),
                    status=self._random_status(),
                )
            )
        created: list[Post] = Post.objects.bulk_create(posts)  # objects now have ids
        # auto_now_add / auto_now overwrite dates in bulk_create,
        # bulk_update does not call save(), so it keeps our values
        for post in created:
            post.created_at, post.updated_at = self._post_dates()
        Post.objects.bulk_update(created, ["created_at", "updated_at"])


        max_tags: int = min(MAX_TAGS_PER_POST, len(tags))
        for post in created:
            tags_count: int = random.randint(MIN_TAGS_PER_POST, max_tags)
            if tags_count:
                post.tags.set(random.sample(tags, tags_count))
        return created

    # ---------- comments ----------
    def _random_comment_body(self) -> str:
        sentences_count: int = random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES)
        return " ".join(self.fake.sentences(nb=sentences_count))

    def _published_posts(self, new_posts: list[Post]) -> list[Post]:
        """Published posts of this run (already in memory); from the DB only if there are none."""
        published: list[Post] = [
            post for post in new_posts if post.status == Post.Status.PUBLISHED
        ]
        if published:
            return published
        return list(
            Post.objects.filter(status=Post.Status.PUBLISHED).only("id", "created_at")
        )

    def _create_comments(self, count: int, new_posts: list[Post]) -> list[Comment]:
        if count == 0:
            return []
        author_ids: list[int] = list(User.objects.values_list("id", flat=True))
        if not author_ids:
            raise CommandError("Cannot create comments: there are no users. Use --users N.")
        publshed_posts: list[Post] = self._published_posts(new_posts)
        if not publshed_posts:
            raise CommandError(
                "Cannot create comments: there are no published posts. Use --posts N."
            )

        comments: list[Comment] = [
            Comment(
                post_id=random.choice(publshed_posts),
                author_id=random.choice(author_ids),
                body=self._random_comment_body(),
            )
            for _ in range(count)
        ]
        created: list[Comment] = Comment.objects.bulk_create(comments)

        # comment date: between its post's created_at (from memory) and now
        for comment in created:
            comment.created_at = self._random_moment_between(comment.post.created_at, self.now)
        Comment.objects.bulk_update(created, ["created_at"])
        return created
