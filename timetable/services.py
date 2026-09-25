from django.core.exceptions import ValidationError
from django.db import transaction

from allocations.models import SubjectAllocation

from .models import (
    TimetablePeriod,
    TimetablePeriodTemplateBlock,
    TimetableRequirement,
)


def sync_timetable_requirements(timetable):
    """
    Create missing timetable requirements for active subject allocations.

    Existing requirements are never modified or recreated automatically.
    Only allocations belonging to active classes for the timetable's
    school and term are considered.
    """

    allocations = (
        SubjectAllocation.objects.filter(
            school_class__school=timetable.school,
            school_class__is_active=True,
            term=timetable.term,
        )
        .select_related(
            "school_class",
            "subject",
            "teacher",
        )
    )

    existing_allocation_ids = set(
        timetable.requirements.values_list(
            "allocation_id",
            flat=True,
        )
    )

    missing_requirements = [
        TimetableRequirement(
            timetable=timetable,
            allocation=allocation,
        )
        for allocation in allocations
        if allocation.id not in existing_allocation_ids
    ]

    if missing_requirements:
        TimetableRequirement.objects.bulk_create(
            missing_requirements
        )

    return len(missing_requirements)


def apply_timetable_period_template(timetable, template):
    """
    Apply an active timetable period template to an empty timetable.

    Only days selected by the timetable are imported.
    Existing timetable periods are never modified.
    """

    if template.school_id != timetable.school_id:
        raise ValidationError(
            "The timetable and period template must belong to the same school."
        )

    if not template.is_active:
        raise ValidationError(
            "The selected period template is inactive."
        )

    if timetable.periods.exists():
        raise ValidationError(
            "A period template can only be applied to a timetable "
            "that has no existing periods."
        )

    template_days = {
        day.day: day
        for day in template.days.prefetch_related("blocks")
    }

    missing_days = [
        day
        for day in timetable.days
        if day not in template_days
    ]

    if missing_days:
        missing_labels = ", ".join(missing_days)

        raise ValidationError(
            f"The period template does not define these timetable days: "
            f"{missing_labels}."
        )

    periods = []

    for day in timetable.days:
        template_day = template_days[day]

        blocks = template_day.blocks.filter(
            is_active=True,
        ).order_by("block_number")

        for block in blocks:
            periods.append(
                TimetablePeriod(
                    timetable=timetable,
                    day=day,
                    name=block.name,
                    period_number=block.block_number,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    is_break=(
                        block.block_type
                        == TimetablePeriodTemplateBlock.BlockType.BREAK
                    ),
                    is_active=block.is_active,
                )
            )

    with transaction.atomic():
        TimetablePeriod.objects.bulk_create(periods)

    return len(periods)