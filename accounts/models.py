from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    
    school = models.ForeignKey(
    "schools.School",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="users",
    help_text="The school this user belongs to."
    )

    class Role(models.TextChoices):
        PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Administrator"
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TEACHER,
    )
    
    school_role = models.ForeignKey(
        "schools.SchoolRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Custom role assigned to this user within their school.",
    )

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    other_name = models.CharField(max_length=150, blank=True)

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.other_name]
        return " ".join(p for p in parts if p).strip()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"