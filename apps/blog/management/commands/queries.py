from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.management.commands.seed import CATEGORY_NAMES, EMAIL_DOMAIN, TAG_NAMES
from apps.blog.models import Post
from apps.blog.queries import QUERIES

PREVIEW_ROWS = 5
DATA_CHANGING_QUERIES: frozenset[int] = frozenset({40, 41, 42, 43, 44})
INDENT = "  "

# sample values for the arguments
SAMPLE_PAGE = 2
SAMPLE_DAYS = 30
SAMPLE_MIN_POSTS = 10
SAMPLE_TAG_NAME = "Django ORM"
NAME_PREFIX_LENGTH = 3  # "John Smith" -> search "john smi"
FIRST_CATEGORY = slugify(CATEGORY_NAMES[0])  # python
SECOND_CATEGORY = slugify(CATEGORY_NAMES[1])  # django
LAST_CATEGORY = slugify(CATEGORY_NAMES[-1])  # career
FIRST_TAG = slugify(TAG_NAMES[0])  # python
SECOND_TAG = slugify(TAG_NAMES[1])  # django


def build_query_arguments() -> dict[int, dict[str, Any]]:
    """{number: {argument: value}}. Values from the DB are read once, before measuring."""
    today = timezone.localdate()
    sample_post: Post | None = (
        Post.objects.filter(status=Post.Status.PUBLISHED).select_related("author").first()
    )
    slug: str = sample_post.slug if sample_post else ""
    word: str = sample_post.title.split()[0] if sample_post else ""
    email: str = sample_post.author.email if sample_post else ""
    full_name_part: str = (
        f"{sample_post.author.first_name} "
        f"{sample_post.author.last_name[:NAME_PREFIX_LENGTH]}".lower()
        if sample_post
        else ""
    )
    return {
        4: {"slug": slug},
        7: {"page": SAMPLE_PAGE},
        8: {"word": word},
        9: {"domain": EMAIL_DOMAIN},
        11: {"slugs": [FIRST_CATEGORY, SECOND_CATEGORY]},
        12: {"year": today.year, "month": today.month},
        13: {"days": SAMPLE_DAYS},
        14: {"start": today - timedelta(days=SAMPLE_DAYS), "end": today},
        15: {"email": email.upper()},  # letter case must not matter
        16: {"tag_slug": FIRST_TAG},
        17: {"category_slug": FIRST_CATEGORY},
        21: {"first_slug": FIRST_TAG, "second_slug": SECOND_TAG},
        22: {"text": word},
        34: {"min_posts": SAMPLE_MIN_POSTS},
        37: {"text": full_name_part},
        40: {"name": SAMPLE_TAG_NAME},
        41: {"days": SAMPLE_DAYS},
        42: {"category_slug": FIRST_CATEGORY, "tag_slug": SECOND_TAG},
        43: {"source_slug": LAST_CATEGORY, "target_slug": FIRST_CATEGORY},
    }


class Command(BaseCommand):
    help = "Run the ORM queries from apps/blog/queries.py and count SQL queries."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run only this query (1-50)")
        parser.add_argument("--sql", action="store_true", help="Also print the SQL")

    def handle(self, *args: Any, **options: Any) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is not None and number not in QUERIES:
            raise CommandError(f"Query #{number} does not exist. Use 1-{max(QUERIES)}.")

        arguments: dict[int, dict[str, Any]] = build_query_arguments()
        if number is not None:
            numbers: list[int] = [number]
        else:  # queries 40-44 change data, they run only with --number
            numbers = [n for n in sorted(QUERIES) if n not in DATA_CHANGING_QUERIES]

        for query_number in numbers:
            self._run(query_number, arguments.get(query_number, {}), show_sql)

    def _run(self, number: int, kwargs: dict[str, Any], show_sql: bool) -> None:
        function: Callable[..., Any] = QUERIES[number]
        annotations: list[str] = []
        with CaptureQueriesContext(connection) as context:
            result: Any = function(**kwargs)
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotations)
                result = list(result)  # a QuerySet is lazy: run it INSIDE the "with"

        count: int = len(context.captured_queries)
        word: str = "query" if count == 1 else "queries"
        header: str = f"#{number} {function.__name__} — {count} SQL {word}"
        self.stdout.write(self.style.SUCCESS(header))
        if show_sql:
            for captured in context.captured_queries:
                self.stdout.write(captured["sql"])
        self._print_result(result, annotations)
        self.stdout.write("")

    def _print_result(self, result: Any, annotations: list[str]) -> None:
        if isinstance(result, dict):
            rows: list[Any] = [f"{key}: {value}" for key, value in result.items()]
        elif isinstance(result, list):
            rows = result
        else:
            self.stdout.write(f"{INDENT}{self._format(result, annotations)}")
            return
        for row in rows[:PREVIEW_ROWS]:
            self.stdout.write(f"{INDENT}{self._format(row, annotations)}")
        self.stdout.write(f"{INDENT}({len(rows)} rows)")

    def _format(self, row: Any, annotations: list[str]) -> str:
        if isinstance(row, Model) and annotations:
            values: dict[str, Any] = {name: getattr(row, name) for name in annotations}
            return f"{row} {values}"
        return str(row)
