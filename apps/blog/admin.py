from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.sections import TableSection

from apps.blog.models import Category, Comment, Post, Tag

SECTION_HEIGHT = 300


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


@admin.register(Post)
class PostAdmin(ModelAdmin):
    search_fields = ('title',)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    pass
