from allocations.models import SubjectAllocation

from .models import TimetableRequirement


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