from django.contrib import admin

from unfold.admin import ModelAdmin

from apps.blog.models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    search_fields = ('name',)


@admin.register(Post)
class PostAdmin(ModelAdmin):
    search_fields = ('title',)


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    pass
