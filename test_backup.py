from core.services.backup_service import BackupService

print(BackupService.database_engine())

print(BackupService.backup_directory())

print(BackupService.backup_filename())