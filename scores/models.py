from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


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
        total = self.total_score
        if total >= 75:
            return 'A1'
        elif total >= 70:
            return 'B2'
        elif total >= 65:
            return 'B3'
        elif total >= 60:
            return 'C4'
        elif total >= 55:
            return 'C5'
        elif total >= 50:
            return 'C6'
        elif total >= 45:
            return 'D7'
        elif total >= 40:
            return 'E8'
        else:
            return 'F9'

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.term}: {self.total_score} ({self.grade})"


def get_class_results(school_class, term):
    """
    Returns a list of dicts, one per student, with total score,
    average, and position — sorted by total score descending.
    """
    from students.models import Student

    students = Student.objects.filter(school_class=school_class, is_active=True)
    results = []

    for student in students:
        scores = Score.objects.filter(student=student, term=term)
        if not scores.exists():
            continue
        total = sum(s.total_score for s in scores)
        average = total / scores.count()
        results.append({
            'student': student,
            'scores': scores,
            'total': total,
            'average': round(average, 2),
        })

    results.sort(key=lambda r: r['total'], reverse=True)
    for index, result in enumerate(results, start=1):
        result['position'] = index

    return results


class ReportCardExtra(models.Model):
    """Holds the non-score parts of a report card: remarks and attendance."""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)

    days_present = models.PositiveIntegerField(null=True, blank=True)
    days_school_opened = models.PositiveIntegerField(null=True, blank=True)

    teacher_remark = models.TextField(blank=True)
    principal_remark = models.TextField(blank=True)

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        return f"{self.student} - {self.term} extras"