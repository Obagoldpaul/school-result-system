from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import platform_admin_required

from .models import DatabaseBackup


@login_required
@platform_admin_required
def maintenance_home(request):
    return render(request, "maintenance/home.html")


@login_required
@platform_admin_required
def backup_list(request):

    backups = DatabaseBackup.objects.all()

    return render(
        request,
        "maintenance/backup_list.html",
        {
            "backups": backups
        }
    )