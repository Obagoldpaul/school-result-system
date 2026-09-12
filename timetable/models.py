from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Timetable(models.Model):
    """
    Represents the timetable for one school and one academic term.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="timetables",
    )

    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="timetables",
    )

    name = models.CharField(
        max_length=150,
    )
    
    days = models.JSONField(
        default=list,
        help_text="Days of the week used by this timetable.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_timetables",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "term"],
                name="unique_timetable_school_term",
            )
        ]

        ordering = ["-created_at"]

    def clean(self):
        if not self.school_id or not self.term_id:
            return

        term_school_id = self.term.session.school_id

        if term_school_id != self.school_id:
            raise ValidationError(
                "The timetable school and term school must be the same."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.school}"


class TimetablePeriod(models.Model):
    """
    Defines one period or break within a timetable's daily structure.
    """

    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name="periods",
    )

    name = models.CharField(
        max_length=50,
    )

    period_number = models.PositiveIntegerField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_break = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "period_number"],
                name="unique_timetable_period_number",
            )
        ]

        ordering = ["period_number"]

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError(
                    "Period end time must be after start time."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.timetable.name} - "
            f"{self.name}"
        )

class TeacherAvailability(models.Model):
    """
    Defines when a teacher is available to teach on a particular day.
    """

    class Day(models.TextChoices):
        MONDAY = "MONDAY", "Monday"
        TUESDAY = "TUESDAY", "Tuesday"
        WEDNESDAY = "WEDNESDAY", "Wednesday"
        THURSDAY = "THURSDAY", "Thursday"
        FRIDAY = "FRIDAY", "Friday"
        SATURDAY = "SATURDAY", "Saturday"

    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.CASCADE,
        related_name="timetable_availabilities",
    )

    day = models.CharField(
        max_length=15,
        choices=Day.choices,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "day",
                    "start_time",
                    "end_time",
                ],
                name="unique_teacher_availability_window",
            )
        ]

        ordering = [
            "teacher",
            "day",
            "start_time",
        ]

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError(
                    "Availability end time must be after start time."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.teacher} - "
            f"{self.get_day_display()} "
            f"{self.start_time.strftime('%H:%M')}–"
            f"{self.end_time.strftime('%H:%M')}"
        )

class TimetableRequirement(models.Model):
    """
    Defines how frequently an existing subject allocation
    should appear in the timetable each week.
    """

    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name="requirements",
    )

    allocation = models.ForeignKey(
        "allocations.SubjectAllocation",
        on_delete=models.CASCADE,
        related_name="timetable_requirements",
    )

    lessons_per_week = models.PositiveIntegerField(
        default=1,
        help_text="Number of lesson periods required each week.",
    )

    double_periods = models.PositiveIntegerField(
        default=0,
        help_text="Number of double-period lessons required each week.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "allocation"],
                name="unique_timetable_allocation_requirement",
            )
        ]

        ordering = ["allocation__school_class", "allocation__subject"]

    def clean(self):
        if not self.timetable_id or not self.allocation_id:
            return

        timetable = self.timetable
        allocation = self.allocation

        timetable_school_id = timetable.school_id
        allocation_school_id = allocation.school_class.school_id
        allocation_term_id = allocation.term_id

        if timetable_school_id != allocation_school_id:
            raise ValidationError(
                "The timetable and allocation must belong to the same school."
            )

        if timetable.term_id != allocation_term_id:
            raise ValidationError(
                "The timetable and allocation must belong to the same term."
            )

        if self.double_periods > self.lessons_per_week // 2:
            raise ValidationError(
                "The number of double periods cannot exceed "
                "half of the weekly lessons."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.allocation.subject} - "
            f"{self.allocation.school_class} "
            f"({self.lessons_per_week}/week)"
        )


class TimetableEntry(models.Model):
    """
    Represents one actual lesson placed into a timetable period.
    """

    class Day(models.TextChoices):
        MONDAY = "MONDAY", "Monday"
        TUESDAY = "TUESDAY", "Tuesday"
        WEDNESDAY = "WEDNESDAY", "Wednesday"
        THURSDAY = "THURSDAY", "Thursday"
        FRIDAY = "FRIDAY", "Friday"
        SATURDAY = "SATURDAY", "Saturday"

    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name="entries",
    )

    requirement = models.ForeignKey(
        TimetableRequirement,
        on_delete=models.CASCADE,
        related_name="entries",
    )

    day = models.CharField(
        max_length=15,
        choices=Day.choices,
    )

    period = models.ForeignKey(
        TimetablePeriod,
        on_delete=models.CASCADE,
        related_name="entries",
    )

    class Meta:
        constraints = []

        ordering = ["day", "period__period_number"]

    def clean(self):
        if not self.timetable_id or not self.requirement_id or not self.period_id:
            return

        if self.requirement.timetable_id != self.timetable_id:
            raise ValidationError(
                "The timetable entry and requirement must belong "
                "to the same timetable."
            )

        if self.period.timetable_id != self.timetable_id:
            raise ValidationError(
                "The timetable entry and period must belong "
                "to the same timetable."
            )

        if self.period.is_break:
            raise ValidationError(
                "A lesson cannot be scheduled during a break period."
            )

        if not self.period.is_active:
            raise ValidationError(
                "A lesson cannot be scheduled in an inactive period."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_day_display()} - "
            f"{self.period.name} - "
            f"{self.requirement.allocation.subject}"
        )