from django.db import migrations, models


def backup_old_permissions(apps, schema_editor):
    """
    Back up the existing SchoolRole -> Django Permission
    assignments before changing the relationship.

    We store the permission as app_label.codename so that
    we can reconnect it to the new schools.Permission model.
    """

    schema_editor.execute("""
        CREATE TEMPORARY TABLE schoolrole_permission_backup (
            schoolrole_id bigint NOT NULL,
            permission_code varchar(100) NOT NULL
        )
    """)

    schema_editor.execute("""
        INSERT INTO schoolrole_permission_backup (
            schoolrole_id,
            permission_code
        )
        SELECT
            srp.schoolrole_id,
            ct.app_label || '.' || ap.codename
        FROM schools_schoolrole_permissions srp
        INNER JOIN auth_permission ap
            ON ap.id = srp.permission_id
        INNER JOIN django_content_type ct
            ON ct.id = ap.content_type_id
    """)


def clear_old_permissions(apps, schema_editor):
    """
    Remove the old Django-permission relationships.

    The assignments have already been safely backed up above.

    This is necessary because the existing through table contains
    auth_permission IDs, while the new relationship will reference
    schools_permission IDs.
    """

    schema_editor.execute("""
        DELETE FROM schools_schoolrole_permissions
    """)


def restore_new_permissions(apps, schema_editor):
    """
    Restore the old role assignments using the new
    Paul SchoolHub Permission catalogue.

    Only permissions that have a matching custom Permission.code
    are restored.
    """

    schema_editor.execute("""
        INSERT INTO schools_schoolrole_permissions (
            schoolrole_id,
            permission_id
        )
        SELECT DISTINCT
            backup.schoolrole_id,
            permission.id
        FROM schoolrole_permission_backup backup
        INNER JOIN schools_permission permission
            ON permission.code = backup.permission_code
    """)


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0006_permission"),
    ]

    operations = [

        # ---------------------------------------------------------
        # 1. Preserve existing role permissions
        # ---------------------------------------------------------

        migrations.RunPython(
            backup_old_permissions,
            migrations.RunPython.noop,
        ),

        # ---------------------------------------------------------
        # 2. Remove the old auth.Permission relationships
        #
        # The data is already safely stored in the temporary
        # backup table.
        # ---------------------------------------------------------

        migrations.RunPython(
            clear_old_permissions,
            migrations.RunPython.noop,
        ),

        # ---------------------------------------------------------
        # 3. Change SchoolRole.permissions from:
        #
        #     auth.Permission
        #
        # to:
        #
        #     schools.Permission
        # ---------------------------------------------------------

        migrations.AlterField(
            model_name="schoolrole",
            name="permissions",
            field=models.ManyToManyField(
                blank=True,
                related_name="school_roles",
                to="schools.permission",
            ),
        ),

        # ---------------------------------------------------------
        # 4. Restore matching permissions
        # ---------------------------------------------------------

        migrations.RunPython(
            restore_new_permissions,
            migrations.RunPython.noop,
        ),
    ]