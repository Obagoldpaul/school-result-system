from django.urls import path
from . import views

urlpatterns = [
    path("", views.maintenance_home, name="maintenance_home"),
    
    path(
        "status/",
        views.maintenance_status,
        name="maintenance_status",
    ),
    
    path("backups/", views.backup_list, name="backup_list"),
    
    path(
        "backups/create/",
        views.create_backup,
        name="create_backup",
    ),
    
    path(
        "backups/download/<int:backup_id>/",
        views.download_backup,
        name="download_backup",
    ),
    
    path(
        "backups/restore/<int:backup_id>/",
        views.restore_backup,
        name="restore_backup",
    ),
    
    path(
        "backups/download-pre-restore/<str:filename>/",
        views.download_pre_restore_backup,
        name="download_pre_restore_backup",
    ),
    
    path(
        "backups/delete/<int:backup_id>/",
        views.delete_backup,
        name="delete_backup",
    ),
]