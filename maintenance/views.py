from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.decorators import platform_admin_required

from .models import DatabaseBackup

import os
import subprocess

from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.shortcuts import redirect
from django.http import FileResponse
from django.shortcuts import get_object_or_404

@login_required
@platform_admin_required
def maintenance_home(request):
    return render(request, "maintenance/home.html")


@login_required
@platform_admin_required
def create_backup(request):

    try:

        create_database_backup()

        messages.success(
            request,
            "Database backup created successfully.",
        )

    except Exception as e:

        messages.error(
            request,
            f"Database backup failed: {e}",
        )

    return redirect("backup_list")

def create_database_backup(pre_restore=False):

    backup_dir = os.path.join(
        settings.MEDIA_ROOT,
        "backups",
    )

    os.makedirs(
        backup_dir,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    if pre_restore:
        filename = (
            f"schoolhub_pre_restore_{timestamp}.sql"
        )
    else:
        filename = (
            f"schoolhub_backup_{timestamp}.sql"
        )

    filepath = os.path.join(
        backup_dir,
        filename,
    )

    database = connection.settings_dict

    pg_dump_path = settings.PG_DUMP_PATH

    command = [
        pg_dump_path,
        "-h",
        database["HOST"],
        "-p",
        str(database["PORT"]),
        "-U",
        database["USER"],
        "-d",
        database["NAME"],
        "-f",
        filepath,
    ]

    env = os.environ.copy()

    env["PGPASSWORD"] = database["PASSWORD"]

    try:

        subprocess.run(
            command,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        size = os.path.getsize(filepath)

        backup = DatabaseBackup.objects.create(
            filename=filename,
            size=size,
        )

        return backup

    except Exception:

        if os.path.exists(filepath):
            os.remove(filepath)

        raise

@login_required
@platform_admin_required
def download_backup(request, backup_id):

    backup = get_object_or_404(
        DatabaseBackup,
        id=backup_id,
    )

    backup_path = os.path.join(
        settings.MEDIA_ROOT,
        "backups",
        backup.filename,
    )

    if not os.path.exists(backup_path):
        messages.error(
            request,
            "Backup file could not be found.",
        )

        return redirect("backup_list")

    return FileResponse(
        open(backup_path, "rb"),
        as_attachment=True,
        filename=backup.filename,
    )

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
    
@login_required
@platform_admin_required
def delete_backup(request, backup_id):

    if request.method != "POST":
        return redirect("backup_list")

    backup = get_object_or_404(
        DatabaseBackup,
        id=backup_id,
    )

    backup_path = os.path.join(
        settings.MEDIA_ROOT,
        "backups",
        backup.filename,
    )

    try:

        if os.path.exists(backup_path):
            os.remove(backup_path)

        backup.delete()

        messages.success(
            request,
            "Database backup deleted successfully.",
        )

    except Exception as e:

        messages.error(
            request,
            f"Database backup deletion failed: {e}",
        )

    return redirect("backup_list")