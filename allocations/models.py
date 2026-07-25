from django.db import models


class SubjectAllocation(models.Model):
    """Assigns a teacher to teach a subject in a specific class, for a specific term."""
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='allocations')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.CASCADE)
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('subject', 'school_class', 'term')

    def __str__(self):
        return f"{self.teacher} teaches {self.subject} to {self.school_class} ({self.term})"