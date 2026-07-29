from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'phone_number', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'phone_number')}),
    )


admin.site.register(User, CustomUserAdmin)

def has_permission(request):
    user = request.user
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.role in [User.Role.ADMIN, User.Role.PRINCIPAL]


admin.site.has_permission = has_permission