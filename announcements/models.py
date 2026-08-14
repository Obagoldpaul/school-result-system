from django.db import models


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = 'ALL', 'Everyone'
        STUDENTS = 'STUDENTS', 'All Students'
        STAFF = 'STAFF', 'All Staff'

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='announcements',
    )

    title = models.CharField(max_length=200)

    body = models.TextField()

    image = models.ImageField(
        upload_to='announcements/',
        blank=True,
        null=True
    )

    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.ALL
    )

    # Pin important announcements to the top
    pinned = models.BooleanField(
        default=False,
        help_text='Pinned announcements appear at the top.'
    )

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return self.title


class AnnouncementRead(models.Model):
    """
    Records that a user has read an announcement.
    """

    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='read_records'
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='announcement_reads'
    )

    read_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user'],
                name='unique_announcement_read'
            )
        ]

        ordering = ['-read_at']

    def __str__(self):
        return (
            f'{self.user} read '
            f'{self.announcement}'
        )


def get_announcements_for_user(user, limit=None):
    """Returns announcements relevant to the user's school and role."""

    from accounts.permissions import is_student, is_staff_member

    if not user.is_authenticated or not user.school:
        return Announcement.objects.none()

    qs = Announcement.objects.filter(
        school=user.school
    )

    if is_student(user):
        qs = qs.filter(
            audience__in=[
                Announcement.Audience.ALL,
                Announcement.Audience.STUDENTS,
            ]
        )

    elif is_staff_member(user):
        qs = qs.filter(
            audience__in=[
                Announcement.Audience.ALL,
                Announcement.Audience.STAFF,
            ]
        )

    else:
        qs = qs.filter(
            audience=Announcement.Audience.ALL
        )

    if limit:
        qs = qs[:limit]

    return qs