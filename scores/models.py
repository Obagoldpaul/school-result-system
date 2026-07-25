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
        return f"{self.student} - {self.subject} - {self.term}: {self.total_score}"