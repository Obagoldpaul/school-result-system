from django.db import models


class Subject(models.Model):

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name="subjects",
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=100
    )

    code = models.CharField(
        max_length=20,
        blank=True
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_subjects',
        help_text="Leave blank if this is a standalone subject. Set this if it's a component of a combined subject."
    )

    is_elective = models.BooleanField(
        default=False,
        help_text="Check this if students choose between alternatives (e.g. CRS vs IRS)."
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_subject_name_per_school'
            ),
            models.UniqueConstraint(
                fields=['school', 'code'],
                name='unique_subject_code_per_school'
            ),
        ]

    def __str__(self):
        return self.name


class ClassSubject(models.Model):
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('school_class', 'subject')

    def __str__(self):
        return f"{self.school_class} - {self.subject}"