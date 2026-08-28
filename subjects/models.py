from django.db import models


class Subject(models.Model):
    
    class SubjectLevel(models.TextChoices):
        PRIMARY = "PRIMARY", "Primary"
        SECONDARY = "SECONDARY", "Secondary"

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name="subjects",
    )
    
    level = models.CharField(
        max_length=10,
        choices=SubjectLevel.choices,
        default=SubjectLevel.SECONDARY,
        help_text="Academic level this subject belongs to.",
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
                fields=['school', 'name', 'level'],
                name='unique_subject_name_per_school'
            ),
            models.UniqueConstraint(
                fields=['school', 'code', 'level'],
                name='unique_subject_code_per_school'
            ),
        ]

    def __str__(self):
        return self.name


class ClassSubject(models.Model):
    school_class = models.ForeignKey(
        'students.SchoolClass',
        on_delete=models.CASCADE
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('school_class', 'subject')

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.school_class_id
            and self.subject_id
            and self.school_class.school_id != self.subject.school_id
        ):
            raise ValidationError(
                "The class and subject must belong to the same school."
            )

        # --------------------------------------------------
        # CLASS SECTION → SUBJECT LEVEL VALIDATION
        # --------------------------------------------------

        if self.school_class_id and self.subject_id:

            section = self.school_class.section
            subject_level = self.subject.level

            primary_sections = [
                self.school_class.Section.PRE_PRIMARY,
                self.school_class.Section.PRIMARY,
            ]

            secondary_sections = [
                self.school_class.Section.JUNIOR_SECONDARY,
                self.school_class.Section.SENIOR_SECONDARY,
            ]

            if (
                section in primary_sections
                and subject_level != Subject.SubjectLevel.PRIMARY
            ):
                raise ValidationError(
                    "Primary and Pre-Primary classes can only be assigned Primary subjects."
                )

            if (
                section in secondary_sections
                and subject_level != Subject.SubjectLevel.SECONDARY
            ):
                raise ValidationError(
                    "Junior and Senior Secondary classes can only be assigned Secondary subjects."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school_class} - {self.subject}"