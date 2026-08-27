from django.http import JsonResponse
from django.urls import path

from .permissions import is_platform_admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import UserAdminForm, UserAdminAddForm

from .models import User
from schools.models import SchoolRole


class CustomUserAdmin(UserAdmin):
    
    model = User
    
    form = UserAdminForm
    
    add_form = UserAdminAddForm
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        school_role_field = form.base_fields.get("school_role")

        if school_role_field:
            if obj and obj.school:
                # Editing an existing user:
                # show only roles belonging to that user's school.
                school_role_field.queryset = (
                    obj.school.roles.filter(is_active=True)
                )
            else:
                # Creating a new user:
                # Do not show roles until a school has been selected.
                school_role_field.queryset = (
                    school_role_field.queryset.none()
                )

        return form
    
    def school_roles(self, request, school_id):

        roles = (
            SchoolRole.objects
            .filter(
                school_id=school_id,
                is_active=True,
            )
            .order_by("name")
        )

        return JsonResponse({
            "roles": [
                {
                    "id": role.id,
                    "name": str(role),
                }
                for role in roles
            ]
        })
    
        
    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                "school-roles/<int:school_id>/",
                self.admin_site.admin_view(self.school_roles),
                name="user_school_roles",
            ),
        ]

        return custom_urls + urls

    list_display = [
        "username",
        "email",
        "school",
        "school_role",
        "role",
        "phone_number",
        "is_staff",
        "is_active",
    ]

    list_filter = [
        "school",
        "school_role",
        "role",
        "is_staff",
        "is_active",
    ]

    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "school__name",
        "school_role__name",
    ]

    fieldsets = UserAdmin.fieldsets + (
        (
            "School & Role",
            {
                "fields": (
                    "school",
                    "school_role",
                    "role",
                )
            },
        ),
        (
            "Extra Info",
            {
                "fields": (
                    "phone_number",
                    "other_name",
                )
            },
        ),
    )

        
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
        (
            "School & Role",
            {
                "fields": (
                    "school",
                    "school_role",
                    "role",
                ),
            },
        ),
        (
            "Extra Info",
            {
                "fields": (
                    "phone_number",
                    "other_name",
                ),
            },
        ),
    )



# Register User ONLY ONCE
admin.site.register(User, CustomUserAdmin)



def has_permission(request):
    return is_platform_admin(request.user)


admin.site.has_permission = has_permission
