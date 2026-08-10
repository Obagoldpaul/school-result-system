from django.db import models
from django.core.exceptions import PermissionDenied


class AcademicSession(models.Model):
    """e.g. 2025/2026"""

    school = models.ForeignKey(
    'schools.School',
    on_delete=models.PROTECT,
    related_name='academic_sessions'
    )

    name = models.CharField(max_length=20)

    is_current = models.BooleanField(
        default=False
    )
    
    class Meta:
        unique_together = ('school', 'name')

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.filter(
                school=self.school,
                is_current=True
            ).exclude(
                pk=self.pk
            ).update(
                is_current=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Term(models.Model):

    class TermName(models.TextChoices):
        FIRST = 'FIRST', 'First Term'
        SECOND = 'SECOND', 'Second Term'
        THIRD = 'THIRD', 'Third Term'

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='terms'
    )

    name = models.CharField(
        max_length=10,
        choices=TermName.choices
    )

    is_current = models.BooleanField(
        default=False
    )

    is_published = models.BooleanField(
        default=False,
        help_text="Check this when results are ready for students to view."
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('session', 'name')

    def save(self, *args, **kwargs):

        if self.is_current:

        # Deactivate other current terms in the same school.
            Term.objects.filter(
                session__school=self.session.school,
            is_current=True
        ).exclude(
            pk=self.pk
        ).update(
            is_current=False
        )

        # Make this term's session the current session
        # for this school.
        AcademicSession.objects.filter(
            school=self.session.school,
            is_current=True
        ).exclude(
            pk=self.session_id
        ).update(
            is_current=False
        )

        AcademicSession.objects.filter(
            pk=self.session_id
        ).update(
            is_current=True
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_name_display()} - {self.session}"


class SchoolSettings(models.Model):
    """
    Singleton model for school information.
    Only one record should ever exist.
    """

    school_name = models.CharField(max_length=200)

    school_logo = models.ImageField(
        upload_to="school/",
        blank=True,
        null=True,
    )

    school_address = models.TextField(blank=True)

    school_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    school_email = models.EmailField(blank=True)

    principal_name = models.CharField(
        max_length=100,
        blank=True,
    )

    principal_signature = models.ImageField(
        upload_to="signatures/",
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("School settings cannot be deleted.")

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.school_name