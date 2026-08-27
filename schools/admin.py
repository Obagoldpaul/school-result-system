from django.contrib import admin
from .models import (
    School,
    SchoolRole,
    SchoolSubscription,
    SubscriptionPackage,
    Feature,
    PlatformSettings,
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "email",
    )

    list_filter = (
        "is_active",
    )

@admin.register(SchoolRole)
class SchoolRoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "school",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "school",
        "is_active",
    )

    search_fields = (
        "name",
        "school__name",
    )

    filter_horizontal = (
        "permissions",
    )


@admin.register(SubscriptionPackage)
class SubscriptionPackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "is_active",
    )

    list_filter = (
        "name",
        "is_active",
    )


@admin.register(SchoolSubscription)
class SchoolSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "package",
        "start_date",
        "end_date",
        "is_active",
    )

    list_filter = (
        "package",
        "is_active",
    )

    search_fields = (
        "school__name",
        "school__code",
    )