from django.db import models


class SubjectAllocation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Scores Submitted'
        REVIEWED = 'REVIEWED', 'Reviewed'
        APPROVED = 'APPROVED', 'Principal Approved'
        PUBLISHED = 'PUBLISHED', 'Published'

    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='allocations')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    class_teacher_comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('subject', 'school_class', 'term')

    def __str__(self):
        return f"{self.teacher} teaches {self.subject} to {self.school_class} ({self.term}) [{self.get_status_display()}]"