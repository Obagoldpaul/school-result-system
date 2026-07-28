from django.db import models
from django.conf import settings


class Department(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Science, Art, Commercial

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    name = models.CharField(max_length=20, unique=True)  # JSS1, JSS2, JSS3, SSS1, SSS2, SSS3
    is_senior = models.BooleanField(default=False)  # True for SSS classes

    def __str__(self):
        return self.name


class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile'
    )
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    admission_number = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female')], blank=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    elective_subjects = models.ManyToManyField(
        'subjects.Subject', blank=True,
        limit_choices_to={'is_elective': True},
        related_name='enrolled_students'
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.school_class}"