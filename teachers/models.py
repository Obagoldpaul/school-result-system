from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Teacher(models.Model):

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
    ]


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile"
    )


    # ==========================
    # PERSONAL INFORMATION
    # ==========================

    passport = models.ImageField(
        upload_to="teachers/passports/",
        blank=True,
        null=True
    )


    date_of_birth = models.DateField(
        blank=True,
        null=True
    )


    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True
    )


    phone_number = models.CharField(
        max_length=20,
        blank=True
    )


    home_address = models.TextField(
        blank=True
    )


    state_of_origin = models.CharField(
        max_length=100,
        blank=True
    )


    local_government = models.CharField(
        max_length=100,
        blank=True
    )



    # ==========================
    # PROFESSIONAL INFORMATION
    # ==========================

    staff_id = models.CharField(
        max_length=20,
    )


    qualification = models.CharField(
        max_length=150,
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


    employment_date = models.DateField(
        blank=True,
        null=True
    )



    # ==========================
    # SCHOOL RESPONSIBILITY
    # ==========================

    is_class_teacher = models.BooleanField(
        default=False
    )


    assigned_class = models.ForeignKey(
        "students.SchoolClass",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select only if this teacher is a class teacher"
    )


    is_active = models.BooleanField(
        default=True
    )
    
    @property
    def school(self):
        return self.user.school
    
    def clean(self):

        if not self.user_id:
            return

        teacher_school = self.user.school

        if not teacher_school:
            raise ValidationError(
                "The teacher's user account must belong to a school."
            )

        if (
            self.assigned_class_id
            and self.assigned_class.school_id != teacher_school.id
        ):
            raise ValidationError(
                "The teacher's assigned class must belong to the same school as the teacher."
            )



    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username}"
            f" ({self.staff_id})"
        )