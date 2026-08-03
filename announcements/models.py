from django.db import models


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = 'ALL', 'Everyone'
        STUDENTS = 'STUDENTS', 'All Students'
        STAFF = 'STAFF', 'All Staff'

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


def get_announcements_for_user(user, limit=None):
    """Returns announcements relevant to this user's role."""
    from accounts.permissions import is_student, is_staff_member

    qs = Announcement.objects.all()
    if is_student(user):
        qs = qs.filter(audience__in=[Announcement.Audience.ALL, Announcement.Audience.STUDENTS])
    elif is_staff_member(user):
        qs = qs.filter(audience__in=[Announcement.Audience.ALL, Announcement.Audience.STAFF])
    else:
        qs = qs.filter(audience=Announcement.Audience.ALL)

    if limit:
        qs = qs[:limit]
    return qs