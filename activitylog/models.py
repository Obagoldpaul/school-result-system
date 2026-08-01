from django.db import models


class ActivityLog(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.description} ({self.created_at:%d %b %Y %H:%M})"


def log_activity(user, description):
    ActivityLog.objects.create(user=user, description=description)