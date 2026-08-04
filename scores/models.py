from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from academics.utils import get_term_order


class Score(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='scores')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)

    ca_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(40)]
    )
    exam_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(60)]
    )

    recorded_by = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'term')

    @property
    def total_score(self):
        return self.ca_score + self.exam_score

    @property
    def grade(self):
        from .reports import _grade_from_total
        return _grade_from_total(self.total_score)

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.term}: {self.total_score} ({self.grade})"



class ReportCardExtra(models.Model):
    """Holds the non-score parts of a report card: remarks and attendance."""

    class HabitRating(models.TextChoices):
        A = 'A', 'A'
        B = 'B', 'B'
        C = 'C', 'C'
        D = 'D', 'D'
        E = 'E', 'E'
        F = 'F', 'F'

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)

    days_present = models.PositiveIntegerField(null=True, blank=True)
    days_school_opened = models.PositiveIntegerField(null=True, blank=True)

    teacher_remark = models.TextField(blank=True)
    principal_remark = models.TextField(blank=True)

    responsibility = models.CharField(max_length=1, choices=HabitRating.choices, blank=True)
    leadership = models.CharField(max_length=1, choices=HabitRating.choices, blank=True)
    hardworking = models.CharField(max_length=1, choices=HabitRating.choices, blank=True)
    neatness = models.CharField(max_length=1, choices=HabitRating.choices, blank=True)

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        return f"{self.student} - {self.term} extras"




def is_class_term_fully_published(school_class, term):
    """True only if every SubjectAllocation for this class/term has reached PUBLISHED status."""
    from allocations.models import SubjectAllocation
    allocations = SubjectAllocation.objects.filter(school_class=school_class, term=term)
    if not allocations.exists():
        return False
    return not allocations.exclude(status=SubjectAllocation.Status.PUBLISHED).exists()