from django.db import models


class DatabaseBackup(models.Model):
    filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    size = models.PositiveBigIntegerField(default=0)
    is_pre_restore = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename