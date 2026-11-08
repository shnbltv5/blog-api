from django.contrib import admin
from django.db.models import Count, QuerySet, TextField
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import Truncator

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

SECTION_HEIGHT = 300
COMMENT_PREVIEW_LENGTH = 60
COMMENTS_PER_PAGE = 10
POST_CHANGELIST = 'admin:blog_post_changelist'
COMMENT_CHANGELIST = 'admin:blog_comment_changelist'
TAG_CHANGE = 'admin:blog_tag_change'


# ---------- Category & Tag ----------
class CategoryPostsSection(TableSection):
    verbose_name = 'Posts in this category'
    related_name = 'posts'
    fields = ['title', 'status', 'created_at']
    height = SECTION_HEIGHT


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'posts_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_sections = [CategoryPostsSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .annotate(posts_total=Count('posts', distinct=True))  # 1 query with COUNT
            .prefetch_related('posts')  # posts for the section in one query
        )

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: Category) -> int:
        return obj.posts_total


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'posts_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(posts_total=Count('posts', distinct=True))

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: Tag) -> int:
        return obj.posts_total


# ---------- Post ----------
class CommentInline(TabularInline):
    model = Comment
    fields = ('author', 'body', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('author',)
    extra = 0  # no empty rows
    per_page = COMMENTS_PER_PAGE  # 10 per page
    tab = True  # own tab in the post form


class PostCommentsSection(TableSection):
    verbose_name = 'Comments'
    related_name = 'comments'
    fields = ['author', 'short_body', 'created_at']
    height = SECTION_HEIGHT

    def short_body(self, instance: Comment) -> str:
        return Truncator(instance.body).chars(COMMENT_PREVIEW_LENGTH)


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # ----- list page -----
    list_display = (
        'post_header',
        'status_label',
        'category',
        'tags_dropdown',
        'comments_count',
        'created_at',
    )
    list_filter = (
        ('status', ChoicesDropdownFilter),
        ('category', RelatedDropdownFilter),
        ('tags', MultipleRelatedDropdownFilter),
        ('author', AutocompleteSelectFilter),
        ('created_at', RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ('title', 'body', 'author__email')
    list_select_related = ('author', 'category')
    list_sections = [PostCommentsSection]

    # ----- change page -----
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ('author', 'category', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    formfield_overrides = {TextField: {'widget': WysiwygWidget}}
    warn_unsaved_form = True
    inlines = [CommentInline]
    fieldsets = (
        ('Content', {'classes': ['tab'], 'fields': ('title', 'slug', 'body')}),
        ('Classification', {'classes': ['tab'], 'fields': ('category', 'tags', 'status')}),
        ('Meta', {'classes': ['tab'], 'fields': ('author', 'created_at', 'updated_at')}),
    )

    # ----- actions -----
    actions = ['publish_selected', 'move_to_drafts']  # checkboxes + dropdown
    actions_row = ['toggle_status']  # in every row
    actions_list = ['publish_all_drafts']  # button above the list
    actions_detail = ['open_comments']  # button on the post page
    actions_submit_line = ['save_and_publish']  # next to Save

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        return (
            super()
            .get_queryset(request)
            .annotate(comments_total=Count('comments', distinct=True))
            .prefetch_related('tags', 'comments__author')
        )

    # ----- columns -----
    @display(description='Post', header=True, ordering='title')
    def post_header(self, obj: Post) -> list[str]:
        return [obj.title, obj.author.email]

    @display(
        description='Status',
        ordering='status',
        label={Post.Status.PUBLISHED: 'success', Post.Status.DRAFT: 'warning'},
    )
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description='Tags', dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict:
        tags: list[Tag] = list(obj.tags.all())  # from prefetch, no query; .count() would query
        return {
            'title': f'{len(tags)} tags',
            'striped': True,
            'items': [
                {'title': tag.name, 'link': reverse(TAG_CHANGE, args=[tag.pk])} for tag in tags
            ],
        }

    @display(description='Comments', ordering='comments_total')
    def comments_count(self, obj: Post) -> int:
        return obj.comments_total

    # ----- bulk actions (checkboxes): request, queryset -----
    @action(description='Publish selected', icon='publish', permissions=['change'])
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated: int = queryset.update(status=Post.Status.PUBLISHED)
        self.message_user(request, f'Published: {updated}')

    @action(description='Move to drafts', icon='edit_note', permissions=['change'])
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated: int = queryset.update(status=Post.Status.DRAFT)
        self.message_user(request, f'Moved to drafts: {updated}')

    # ----- row action: request, object_id -----
    @action(
        description='Publish / unpublish',
        icon='swap_horiz',
        url_path='toggle-status',
        permissions=['change'],
    )
    def toggle_status(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post: Post = get_object_or_404(Post, pk=object_id)
        is_published: bool = post.status == Post.Status.PUBLISHED
        post.status = Post.Status.DRAFT if is_published else Post.Status.PUBLISHED
        post.save(update_fields=['status', 'updated_at'])
        self.message_user(request, f"'{post.title}' is now {post.get_status_display()}")
        return redirect(reverse(POST_CHANGELIST))

    # ----- list action (above the list): request -----
    @action(
        description='Publish all drafts',
        icon='done_all',
        url_path='publish-all-drafts',
        permissions=['change'],
    )
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        updated: int = Post.objects.filter(status=Post.Status.DRAFT).update(
            status=Post.Status.PUBLISHED
        )
        self.message_user(request, f'Published all drafts: {updated}')
        return redirect(reverse(POST_CHANGELIST))

    # ----- detail action (on the post page): request, object_id -----
    @action(description='Open comments', icon='chat', url_path='open-comments')
    def open_comments(self, request: HttpRequest, object_id: int) -> HttpResponse:
        return redirect(reverse(COMMENT_CHANGELIST) + f'?post__id__exact={object_id}')

    # ----- submit line action (next to Save): request, obj; runs AFTER save -----
    @action(description='Save & publish', permissions=['change'])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=['status'])
        self.message_user(request, f"'{obj.title}' saved and published")


# ---------- Comment ----------
@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ('post_title', 'author', 'short_body', 'created_at')
    list_filter = (
        ('post', AutocompleteSelectFilter),
        ('author', AutocompleteSelectFilter),
        ('created_at', RangeDateTimeFilter),
    )
    list_filter_submit = True  # filters are applied with a button
    search_fields = ('body', 'author__email', 'post__title')
    autocomplete_fields = ('post', 'author')  # search instead of a huge select
    list_select_related = ('post', 'author')  # JOIN: post and author in one query

    @display(description='Post', ordering='post__title')
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description='Body')
    def short_body(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_PREVIEW_LENGTH)
