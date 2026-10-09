from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.validators import validate_document_size, validate_image_size


class RegistrationApplication(models.Model):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="registration_applications",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Applicant account information
    username = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    other_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)

    # Common personal information
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[
            ("MALE", "Male"),
            ("FEMALE", "Female"),
        ],
    )
    nationality = models.CharField(
        max_length=100,
        default="Nigerian",
    )
    state_of_origin = models.CharField(
        max_length=100,
        blank=True,
    )
    local_government = models.CharField(
        max_length=100,
        blank=True,
    )
    religion = models.CharField(
        max_length=50,
        blank=True,
    )
    home_address = models.TextField(blank=True)

    passport = models.ImageField(
        upload_to="registration_applications/passports/",
        blank=True,
        null=True,
        validators=[validate_image_size],
    )

    # Student application information
    requested_class = models.ForeignKey(
        "students.SchoolClass",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registration_applications",
    )
    requested_department = models.ForeignKey(
        "students.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="registration_applications",
    )

    guardian_name = models.CharField(
        max_length=150,
        blank=True,
    )
    guardian_relationship = models.CharField(
        max_length=100,
        blank=True,
    )
    guardian_phone = models.CharField(
        max_length=20,
        blank=True,
    )
    guardian_email = models.EmailField(blank=True)

    blood_group = models.CharField(
        max_length=10,
        blank=True,
    )
    genotype = models.CharField(
        max_length=10,
        blank=True,
    )
    medical_condition = models.TextField(blank=True)
    previous_school = models.CharField(
        max_length=200,
        blank=True,
    )

    # Teacher application information
    qualification = models.CharField(
        max_length=150,
        blank=True,
    )
    certificate = models.FileField(
        upload_to="registration_applications/certificates/",
        blank=True,
        null=True,
        validators=[validate_document_size],
    )
    years_of_experience = models.PositiveIntegerField(default=0)
    
    bank_name = models.CharField(
        max_length=100,
        blank=True,
    )

    account_name = models.CharField(
        max_length=150,
        blank=True,
    )

    account_number = models.CharField(
        max_length=20,
        blank=True,
    )

    # Review information
    submitted_at = models.DateTimeField(auto_now_add=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_registration_applications",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)

    def clean(self):
        if self.requested_class_id:
            if self.requested_class.school_id != self.school_id:
                raise ValidationError(
                    {
                        "requested_class": (
                            "The requested class must belong to the same school "
                            "as the application."
                        )
                    }
                )

        if self.requested_department_id:
            if self.requested_department.school_id != self.school_id:
                raise ValidationError(
                    {
                        "requested_department": (
                            "The requested department must belong to the same "
                            "school as the application."
                        )
                    }
                )

        if self.reviewed_by_id:
            if self.reviewed_by.school_id != self.school_id:
                raise ValidationError(
                    {
                        "reviewed_by": (
                            "The reviewer must belong to the same school "
                            "as the application."
                        )
                    }
                )

    def __str__(self):
        return (
            f"{self.get_role_display()} application - "
            f"{self.get_full_name()}"
        )

    def get_full_name(self):
        parts = [
            self.last_name,
            self.first_name,
            self.other_name,
        ]
        return " ".join(part for part in parts if part).strip()