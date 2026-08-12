from django.db import models
from django.core.exceptions import ValidationError


class SubjectAllocation(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Scores Submitted'
        REVIEWED = 'REVIEWED', 'Reviewed'
        APPROVED = 'APPROVED', 'Principal Approved'
        PUBLISHED = 'PUBLISHED', 'Published'

    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.CASCADE,
        related_name='allocations'
    )

    subject = models.ForeignKey(
        'subjects.Subject',
        on_delete=models.CASCADE
    )

    school_class = models.ForeignKey(
        'students.SchoolClass',
        on_delete=models.CASCADE
    )

    term = models.ForeignKey(
        'academics.Term',
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    class_teacher_comment = models.TextField(
        blank=True
    )

    class Meta:
        unique_together = ('subject', 'school_class', 'term')

    def clean(self):
        if not all([
            self.teacher_id,
            self.subject_id,
            self.school_class_id,
            self.term_id,
        ]):
            return

        teacher_school = self.teacher.school
        subject_school = self.subject.school
        class_school = self.school_class.school
        term_school = self.term.session.school

        if not teacher_school:
            raise ValidationError(
                "The teacher must belong to a school."
            )

        if not subject_school:
            raise ValidationError(
                "The subject must belong to a school."
            )

        if not class_school:
            raise ValidationError(
                "The class must belong to a school."
            )

        if not term_school:
            raise ValidationError(
                "The term must belong to a school."
            )

        schools = {
            teacher_school.id,
            subject_school.id,
            class_school.id,
            term_school.id,
        }

        if len(schools) != 1:
            raise ValidationError(
                "Teacher, subject, class and term must all belong to the same school."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.teacher} teaches {self.subject} "
            f"to {self.school_class} ({self.term}) "
            f"[{self.get_status_display()}]"
        )