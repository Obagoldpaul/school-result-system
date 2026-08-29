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
            is_pre_restore=pre_restore,
        )

        return backup

    except Exception:

        if os.path.exists(filepath):
            os.remove(filepath)

        raise

def restore_database_backup(backup):

    backup_path = os.path.join(
        settings.MEDIA_ROOT,
        "backups",
        backup.filename,
    )

    if not os.path.isfile(backup_path):
        raise FileNotFoundError(
            "The selected backup file could not be found."
        )

    # Create a safety backup before modifying the database.
    safety_backup = create_database_backup(
        pre_restore=True
    )

    database = connection.settings_dict

    env = os.environ.copy()
    env["PGPASSWORD"] = database["PASSWORD"]

    # Recreate the public schema.
    schema_command = [
        settings.PSQL_PATH,
        "-h",
        database["HOST"],
        "-p",
        str(database["PORT"]),
        "-U",
        database["USER"],
        "-d",
        database["NAME"],
        "-c",
        "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
    ]

    try:

        subprocess.run(
            schema_command,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as e:

        raise RuntimeError(
            "Database schema preparation failed. "
            "The selected backup was not restored. "
            f"PostgreSQL error: {e.stderr.strip()}"
        ) from e

    # Restore the selected plain-text SQL dump.
    restore_command = [
        settings.PSQL_PATH,
        "-h",
        database["HOST"],
        "-p",
        str(database["PORT"]),
        "-U",
        database["USER"],
        "-d",
        database["NAME"],
        "-v",
        "ON_ERROR_STOP=1",
        "-f",
        backup_path,
    ]

    try:

        subprocess.run(
            restore_command,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as e:

        raise RuntimeError(
            "Database restore failed after the existing database "
            "schema was cleared. "
            f"Your pre-restore safety backup is: "
            f"{safety_backup.filename}. "
            f"PostgreSQL error: {e.stderr.strip()}"
        ) from e

    return True

@login_required
@platform_admin_required
def restore_backup(request, backup_id):

    backup = get_object_or_404(
        DatabaseBackup,
        id=backup_id,
    )

    if request.method == "GET":
        return render(
            request,
            "maintenance/restore_backup.html",
            {
                "backup": backup,
            },
        )

    if request.method == "POST":

        if request.POST.get("confirm_restore") != "on":

            messages.error(
                request,
                "You must confirm the database restore before continuing.",
            )

            return redirect(
                "restore_backup",
                backup_id=backup.id,
            )

        try:

            restore_database_backup(backup)

            messages.success(
                request,
                (
                    f"Database restored successfully from "
                    f"{backup.filename}."
                ),
            )

        except FileNotFoundError as e:

            messages.error(
                request,
                str(e),
            )

        except RuntimeError as e:

            messages.error(
                request,
                str(e),
            )

        except Exception as e:

            messages.error(
                request,
                f"Database restore failed: {e}",
            )

        return redirect("backup_list")

    return redirect("backup_list")

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