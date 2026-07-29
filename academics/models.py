from django.db import models


class AcademicSession(models.Model):
    """e.g. 2025/2026"""
    name = models.CharField(max_length=20, unique=True)
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Term(models.Model):
    class TermName(models.TextChoices):
        FIRST = 'FIRST', 'First Term'
        SECOND = 'SECOND', 'Second Term'
        THIRD = 'THIRD', 'Third Term'

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=10, choices=TermName.choices)
    is_current = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False, help_text="Check this when results are ready for students to view.")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'name')

    def __str__(self):
        return f"{self.get_name_display()} - {self.session}"


class SchoolSettings(models.Model):
    """Singleton-style settings for the whole school (only one row should exist)."""
    principal_name = models.CharField(max_length=100, blank=True)
    principal_signature = models.ImageField(upload_to='signatures/', blank=True, null=True)

    def __str__(self):
        return "School Settings"