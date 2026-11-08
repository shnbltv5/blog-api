from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from apps.auths.forms import BlogUserChangeForm, BlogUserCreationForm
from apps.auths.models import User

STATE_ON = 'on'
STATE_OFF = 'off'

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = BlogUserChangeForm
    add_form = BlogUserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ('user_header', 'active_label', 'staff_label', 'posts_count')
    list_filter = (
        ('is_active', BooleanRadioFilter),
        ('is_staff', BooleanRadioFilter),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'date_joined')
    filter_horizontal = ('groups', 'user_permissions')
    actions = ['activate_users', 'deactivate_users']

    fieldsets = (
        (
            'Personal info',
            {'classes': ['tab'], 'fields': ('email', 'first_name', 'last_name', 'password')},
        ),
        (
            'Permissions',
            {
                'classes': ['tab'],
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        ('Important dates', {'classes': ['tab'], 'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(posts_total=Count('posts', distinct=True))

    # ----- columns -----
    @display(description='User', header=True, ordering='email')
    def user_header(self, obj: User) -> list[str]:
        initials: str = f'{obj.first_name[:1]}{obj.last_name[:1]}'.upper()
        return [f'{obj.first_name} {obj.last_name}', obj.email, initials]

    @display(
        description='Active',
        ordering='is_active',
        label={STATE_ON: 'success', STATE_OFF: 'danger'},
    )
    def active_label(self, obj: User) -> tuple[str, str]:
        return (STATE_ON, 'Active') if obj.is_active else (STATE_OFF, 'Inactive')

    @display(
        description='Staff',
        ordering='is_staff',
        label={STATE_ON: 'info', STATE_OFF: 'warning'},
    )
    def staff_label(self, obj: User) -> tuple[str, str]:
        return (STATE_ON, 'Staff') if obj.is_staff else (STATE_OFF, 'Regular')

    @display(description='Posts', ordering='posts_total')
    def posts_count(self, obj: User) -> int:
        return obj.posts_total

    # ----- bulk actions -----
    @action(description='Activate selected users', icon='check_circle')
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated: int = queryset.update(is_active=True)  # one UPDATE for all rows
        self.message_user(request, f'Activated: {updated}')

    @action(description='Deactivate selected users', icon='block')
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated: int = queryset.update(is_active=False)
        self.message_user(request, f'Deactivated: {updated}')
