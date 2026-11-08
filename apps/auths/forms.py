from unfold.forms import UserChangeForm, UserCreationForm

from apps.auths.models import User


class BlogUserCreationForm(UserCreationForm):
    """Add-user form: email, names, password twice (hashed in save)."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')
        field_classes = {}


class BlogUserChangeForm(UserChangeForm):
    """Edit-user form: password shown as hash + link 'Reset password'."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
        field_classes = {}
