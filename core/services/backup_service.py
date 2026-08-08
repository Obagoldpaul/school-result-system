from pathlib import Path
from datetime import datetime

from django.conf import settings


class BackupService:
    """
    Handles database backups.
    Supports multiple database engines.
    """

    @staticmethod
    def backup_directory():
        folder = Path(settings.BASE_DIR) / "backups"
        folder.mkdir(exist_ok=True)
        return folder

    @staticmethod
    def database_engine():
        return settings.DATABASES["default"]["ENGINE"]

    @staticmethod
    def backup_filename():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}.sql"