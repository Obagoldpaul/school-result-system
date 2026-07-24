from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        PRINCIPAL = 'PRINCIPAL', 'Principal'
        TEACHER = 'TEACHER', 'Teacher'
        CLASS_TEACHER = 'CLASS_TEACHER', 'Class Teacher'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TEACHER,
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"