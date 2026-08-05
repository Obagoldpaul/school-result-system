from django.db import models
from django.conf import settings


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile"
    )

    staff_id = models.CharField(
        max_length=20,
        unique=True
    )

    passport = models.ImageField(
        upload_to="teachers/passports/",
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    qualification = models.CharField(
        max_length=100,
        blank=True
    )

    certificate = models.FileField(
        upload_to="teachers/certificates/",
        blank=True,
        null=True
    )

    years_of_experience = models.PositiveIntegerField(
        default=0
    )

    nin = models.CharField(
     "NIN",
        max_length=11,
        blank=True
    )

    specialization = models.CharField(
        max_length=150,
        blank=True
    )

    address = models.TextField(
        blank=True
    )

    next_of_kin = models.CharField(
        max_length=100,
        blank=True
    )

    next_of_kin_phone = models.CharField(
        max_length=20,
        blank=True
    )

    employment_date = models.DateField(
        blank=True,
        null=True
    )

    is_class_teacher = models.BooleanField(
        default=False
    )

    assigned_class = models.ForeignKey(
        "students.SchoolClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Only fill this if the teacher is a Class Teacher."
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username}"
            f" ({self.staff_id})"
        )