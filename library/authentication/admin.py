from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from order.models import Order

from .models import CustomUser

admin.site.site_header = 'Library administration'
admin.site.site_title = 'Library admin'
admin.site.index_title = 'Manage users, books, authors and orders'


class CustomUserCreationForm(BaseUserCreationForm):
    """Form for adding a user in the admin panel (password is hashed)."""

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'middle_name', 'last_name', 'role')


class CustomUserChangeForm(UserChangeForm):
    """Form for editing a user in the admin panel."""

    class Meta:
        model = CustomUser
        fields = '__all__'


class UserOrderInline(admin.TabularInline):
    model = Order
    fk_name = 'user'
    extra = 0
    fields = ('book', 'created_at', 'plated_end_at', 'end_at')
    readonly_fields = ('created_at',)
    verbose_name = 'order'
    verbose_name_plural = 'Books issued to this user'
    show_change_link = True


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ('id', 'email', 'last_name', 'first_name', 'middle_name', 'role',
                    'is_active', 'is_staff', 'is_superuser', 'created_at')
    list_display_links = ('id', 'email')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('=id', 'email', 'first_name', 'last_name', 'middle_name')
    search_help_text = 'Search by ID, email or name'
    ordering = ('id',)
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    filter_horizontal = ('groups', 'user_permissions')
    inlines = (UserOrderInline,)

    fieldsets = (
        ('Account', {'fields': ('email', 'password')}),
        ('Personal information', {'fields': ('first_name', 'middle_name', 'last_name')}),
        ('Role in the library', {'fields': ('role', 'is_active')}),
        ('Admin panel permissions', {
            'classes': ('collapse',),
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('created_at', 'updated_at', 'last_login')}),
    )
    add_fieldsets = (
        ('Account', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal information', {
            'classes': ('wide',),
            'fields': ('first_name', 'middle_name', 'last_name', 'role'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Users created in the admin panel can log in right away.
        if not change:
            obj.is_active = True
        super().save_model(request, obj, form, change)
