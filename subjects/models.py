from django.db import models


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='sub_subjects',
        help_text="Leave blank if this is a standalone subject. Set this if it's a component of a combined subject."
    )
    is_elective = models.BooleanField(
        default=False,
        help_text="Check this if students choose between alternatives (e.g. CRS vs IRS)."
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ClassSubject(models.Model):
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('school_class', 'subject')

    def __str__(self):
        return f"{self.school_class} - {self.subject}"