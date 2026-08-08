from django.urls import path
from . import views

urlpatterns = [
    path("", views.maintenance_home, name="maintenance_home"),
    path("backups/", views.backup_list, name="backup_list"),
]