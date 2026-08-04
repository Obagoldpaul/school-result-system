from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        PRINCIPAL = 'PRINCIPAL', 'Principal'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TEACHER,
    )

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    other_name = models.CharField(max_length=150, blank=True)

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.other_name]
        return " ".join(p for p in parts if p).strip()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"