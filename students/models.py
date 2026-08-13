from django.db import models
from django.conf import settings

from django.db import models
from django.core.exceptions import ValidationError


class Department(models.Model):

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name="departments",
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=50
    )

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return self.name

class SchoolClass(models.Model):

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name="classes",
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=50
    )  # JSS1, JSS2, JSS3, SSS1...

    is_senior = models.BooleanField(
        default=False
    )

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return self.name

class Student(models.Model):
    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
    ]

    BLOOD_GROUPS = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    admission_number = models.CharField(
        max_length=20,
    )

    # Learner Identification Number
    lin = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        verbose_name="LIN"
    )

    passport = models.ImageField(
        upload_to="students/passports/",
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

    state_of_origin = models.CharField(
        max_length=100,
        blank=True
    )

    local_government = models.CharField(
        max_length=100,
        blank=True
    )

    nationality = models.CharField(
        max_length=100,
        default="Nigerian"
    )

    religion = models.CharField(
        max_length=50,
        blank=True
    )

    home_address = models.TextField(
        blank=True
    )

    blood_group = models.CharField(
        max_length=5,
        choices=BLOOD_GROUPS,
        blank=True
    )

    genotype = models.CharField(
        max_length=5,
        blank=True
    )

    guardian_name = models.CharField(
        max_length=100,
        blank=True
    )

    guardian_relationship = models.CharField(
        max_length=100,
        blank=True
    )

    guardian_phone = models.CharField(
        max_length=20,
        blank=True
    )

    guardian_email = models.EmailField(
        blank=True
    )

    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True
    )

    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True
    )

    medical_condition = models.TextField(
        blank=True
    )

    admission_date = models.DateField(
        blank=True,
        null=True
    )

    previous_school = models.CharField(
        max_length=200,
        blank=True
    )

    admission_status = models.CharField(
        max_length=20,
        choices=[
            ("ACTIVE", "Active"),
            ("TRANSFERRED", "Transferred"),
            ("GRADUATED", "Graduated"),
            ("WITHDRAWN", "Withdrawn"),
        ],
        default="ACTIVE",
    )

    is_active = models.BooleanField(
        default=True
    )

    elective_subjects = models.ManyToManyField(
        "subjects.Subject",
        blank=True,
        limit_choices_to={"is_elective": True},
        related_name="enrolled_students"
    )

    @property
    def school(self):
        return self.user.school

    def clean(self):
        if not self.user_id:
            return

        student_school = self.user.school

        if not student_school:
            raise ValidationError(
                "The student's user account must belong to a school."
            )

        if (
            self.school_class_id
            and self.school_class.school_id != student_school.id
        ):
            raise ValidationError(
                "The student's class must belong to the same school as the student."
            )

        if (
            self.department_id
            and self.department.school_id != student_school.id
        ):
            raise ValidationError(
                "The student's department must belong to the same school as the student."
            )

    def __str__(self):
        return (
            f"{self.user.get_full_name() or self.user.username}"
            f" - {self.school_class}"
        )