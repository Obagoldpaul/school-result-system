from django.contrib import admin
from .models import DatabaseBackup


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "created_at",
        "size",
    )