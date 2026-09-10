from django.core.exceptions import ValidationError
from django.db import transaction

from .availability import teacher_is_available
from .models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableRequirement,
)


class TimetableGenerationError(Exception):
    """Raised when a timetable cannot be completely generated."""


DAYS = [
    TimetableEntry.Day.MONDAY,
    TimetableEntry.Day.TUESDAY,
    TimetableEntry.Day.WEDNESDAY,
    TimetableEntry.Day.THURSDAY,
    TimetableEntry.Day.FRIDAY,
    TimetableEntry.Day.SATURDAY,
]


def _validate_period_structure(periods):
    """
    Ensure the timetable periods do not overlap.

    This protects the generator from treating overlapping period numbers
    as separate time slots when they actually occur at the same time.
    """

    ordered = sorted(
        periods,
        key=lambda period: (
            period.start_time,
            period.end_time,
            period.period_number,
        ),
    )

    for previous, current in zip(ordered, ordered[1:]):
        if current.start_time < previous.end_time:
            raise TimetableGenerationError(
                "Timetable periods overlap: "
                f"'{previous.name}' and '{current.name}'. "
                "Please correct the period times before generating."
            )


def _build_double_period_pairs(periods):
    """
    Return valid consecutive lesson-period pairs.

    A double period must:
    - use two active, non-break periods
    - have consecutive period numbers
    - have no time gap between the two periods
    """

    pairs = []

    for first, second in zip(periods, periods[1:]):
        if first.period_number + 1 != second.period_number:
            continue

        if first.end_time != second.start_time:
            continue

        pairs.append((first, second))

    return pairs


def _requirement_units(requirements):
    """
    Convert requirements into individual scheduling units.

    Example:
        lessons_per_week=5
        double_periods=1

    becomes:
        double
        single
        single
        single

    Total scheduled periods = 5.
    """

    units = []

    for requirement in requirements:
        lessons = requirement.lessons_per_week
        doubles = requirement.double_periods

        if lessons <= 0:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' must require at least "
                "one lesson per week."
            )

        if doubles > lessons // 2:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' has too many double periods."
            )

        for _ in range(doubles):
            units.append(
                {
                    "requirement": requirement,
                    "length": 2,
                }
            )

        single_lessons = lessons - (doubles * 2)

        for _ in range(single_lessons):
            units.append(
                {
                    "requirement": requirement,
                    "length": 1,
                }
            )

    return units


def _candidate_placements(
    unit,
    lesson_periods,
    double_pairs,
    availability_cache,
):
    """
    Build all placements that satisfy the timetable's structural
    and teacher-availability constraints.

    Conflicts with other scheduled lessons are handled separately
    during the backtracking search.
    """

    requirement = unit["requirement"]
    allocation = requirement.allocation
    teacher = allocation.teacher

    candidates = []

    if unit["length"] == 1:
        for day in DAYS:
            for period in lesson_periods:
                cache_key = (
                    teacher.id,
                    day,
                    period.start_time,
                    period.end_time,
                )

                if cache_key not in availability_cache:
                    availability_cache[cache_key] = teacher_is_available(
                        teacher,
                        day,
                        period.start_time,
                        period.end_time,
                    )

                if not availability_cache[cache_key]:
                    continue

                candidates.append(
                    {
                        "day": day,
                        "periods": (period,),
                    }
                )

    else:
        for day in DAYS:
            for first, second in double_pairs:
                cache_key = (
                    teacher.id,
                    day,
                    first.start_time,
                    second.end_time,
                )

                if cache_key not in availability_cache:
                    availability_cache[cache_key] = teacher_is_available(
                        teacher,
                        day,
                        first.start_time,
                        second.end_time,
                    )

                if not availability_cache[cache_key]:
                    continue

                candidates.append(
                    {
                        "day": day,
                        "periods": (first, second),
                    }
                )

    return candidates


def _placement_is_free(
    placement,
    requirement,
    class_busy,
    teacher_busy,
):
    """
    Check class and teacher conflicts for a proposed placement.
    """

    allocation = requirement.allocation
    class_id = allocation.school_class_id
    teacher_id = allocation.teacher_id
    day = placement["day"]

    for period in placement["periods"]:
        class_key = (
            class_id,
            day,
            period.id,
        )

        teacher_key = (
            teacher_id,
            day,
            period.id,
        )

        if class_key in class_busy:
            return False

        if teacher_key in teacher_busy:
            return False

    return True


def _apply_placement(
    placement,
    requirement,
    class_busy,
    teacher_busy,
    assignments,
):
    """
    Add a placement to the current in-memory schedule.
    """

    allocation = requirement.allocation
    class_id = allocation.school_class_id
    teacher_id = allocation.teacher_id
    day = placement["day"]

    for period in placement["periods"]:
        class_busy.add(
            (
                class_id,
                day,
                period.id,
            )
        )

        teacher_busy.add(
            (
                teacher_id,
                day,
                period.id,
            )
        )

        assignments.append(
            {
                "requirement": requirement,
                "day": day,
                "period": period,
            }
        )


def _remove_placement(
    placement,
    requirement,
    class_busy,
    teacher_busy,
    assignments,
):
    """
    Remove a placement during backtracking.
    """

    allocation = requirement.allocation
    class_id = allocation.school_class_id
    teacher_id = allocation.teacher_id
    day = placement["day"]

    for period in placement["periods"]:
        class_busy.remove(
            (
                class_id,
                day,
                period.id,
            )
        )

        teacher_busy.remove(
            (
                teacher_id,
                day,
                period.id,
            )
        )

        assignments.pop()


def _search_schedule(
    units,
    candidate_map,
    class_busy,
    teacher_busy,
    assignments,
):
    """
    Backtracking search.

    The search always chooses the currently most constrained
    unscheduled unit first. This greatly reduces unnecessary
    combinations while still allowing the generator to backtrack
    when a previous choice makes later scheduling impossible.
    """

    if not units:
        return True

    best_unit = None
    best_candidates = None
    best_index = None

    for index, unit in enumerate(units):
        requirement = unit["requirement"]
        available_candidates = []

        for candidate in candidate_map[index]:
            if _placement_is_free(
                candidate,
                requirement,
                class_busy,
                teacher_busy,
            ):
                available_candidates.append(candidate)

        if not available_candidates:
            return False

        if (
            best_candidates is None
            or len(available_candidates) < len(best_candidates)
        ):
            best_unit = unit
            best_candidates = available_candidates
            best_index = index

    remaining_units = units[:best_index] + units[best_index + 1 :]

    requirement = best_unit["requirement"]

    for candidate in best_candidates:
        _apply_placement(
            candidate,
            requirement,
            class_busy,
            teacher_busy,
            assignments,
        )

        if _search_schedule(
            remaining_units,
            {
                new_index: candidate_map[
                    original_index
                ]
                for new_index, original_index in enumerate(
                    [
                        i
                        for i in range(len(units))
                        if i != best_index
                    ]
                )
            },
            class_busy,
            teacher_busy,
            assignments,
        ):
            return True

        _remove_placement(
            candidate,
            requirement,
            class_busy,
            teacher_busy,
            assignments,
        )

    return False


def generate_timetable(timetable, school):
    """
    Generate a complete timetable for one existing timetable.

    The timetable must:
    - belong to the supplied school
    - be a draft
    - have valid active lesson periods
    - have timetable requirements
    - contain requirements belonging to the same school and term
    - contain only active classes for generation
    - satisfy teacher availability
    - satisfy class and teacher conflict constraints
    - satisfy all required weekly lesson frequencies

    Entries are written to the database only after the complete
    schedule has been successfully found.
    """

    if timetable is None or not timetable.pk:
        raise TimetableGenerationError(
            "A saved timetable is required for generation."
        )

    if school is None:
        raise TimetableGenerationError(
            "A school is required for timetable generation."
        )

    if timetable.school_id != school.id:
        raise TimetableGenerationError(
            "You cannot generate a timetable belonging to another school."
        )

    if timetable.status != Timetable.Status.DRAFT:
        raise TimetableGenerationError(
            "Only draft timetables can be generated."
        )

    if timetable.term.session.school_id != school.id:
        raise TimetableGenerationError(
            "The timetable term does not belong to the timetable's school."
        )

    if timetable.entries.exists():
        raise TimetableGenerationError(
            "This timetable already contains entries. "
            "Clear the existing draft entries before generating again."
        )

    all_periods = list(
        timetable.periods.all().order_by("period_number")
    )

    if not all_periods:
        raise TimetableGenerationError(
            "The timetable has no periods. Add the daily periods first."
        )

    _validate_period_structure(all_periods)

    lesson_periods = [
        period
        for period in all_periods
        if period.is_active and not period.is_break
    ]

    if not lesson_periods:
        raise TimetableGenerationError(
            "The timetable has no active lesson periods."
        )

    double_pairs = _build_double_period_pairs(lesson_periods)

    requirements = list(
        timetable.requirements.select_related(
            "allocation",
            "allocation__teacher",
            "allocation__teacher__user",
            "allocation__subject",
            "allocation__school_class",
            "allocation__term",
        ).order_by(
            "allocation__school_class__name",
            "allocation__subject__name",
        )
    )

    active_requirements = []

    for requirement in requirements:
        allocation = requirement.allocation
        school_class = allocation.school_class
        teacher = allocation.teacher

        if allocation.school_class.school_id != school.id:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' references a class "
                "from another school."
            )

        if allocation.term_id != timetable.term_id:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' references an allocation "
                "from another term."
            )

        if allocation.subject.school_id != school.id:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' references a subject "
                "from another school."
            )

        if teacher.school.id != school.id:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' references a teacher "
                "from another school."
            )

        if teacher.user.school_id != school.id:
            raise TimetableGenerationError(
                f"Requirement '{requirement}' references a teacher "
                "whose user belongs to another school."
            )

        # Inactive classes do not participate in new generation.
        if not school_class.is_active:
            continue

        active_requirements.append(requirement)

    if not active_requirements:
        return []

    units = _requirement_units(active_requirements)

    if not units:
        raise TimetableGenerationError(
            "There are no lessons to generate."
        )

    if any(
        unit["length"] == 2
        for unit in units
    ) and not double_pairs:
        raise TimetableGenerationError(
            "Double periods are required, but the timetable does not "
            "contain two consecutive lesson periods that can form "
            "a double period."
        )

    availability_cache = {}
    candidate_map = {}

    for index, unit in enumerate(units):
        candidates = _candidate_placements(
            unit,
            lesson_periods,
            double_pairs,
            availability_cache,
        )

        if not candidates:
            requirement = unit["requirement"]
            allocation = requirement.allocation

            raise TimetableGenerationError(
                f"Unable to schedule '{allocation.subject}' for "
                f"{allocation.school_class}. No valid "
                f"{'double-period' if unit['length'] == 2 else 'lesson'} "
                "placement satisfies the teacher availability and "
                "timetable period constraints."
            )

        candidate_map[index] = candidates

    class_busy = set()
    teacher_busy = set()
    assignments = []

    # The recursive search uses unit indexes. Keep a simple fixed
    # ordering here; the search itself applies MRV dynamically.
    if not _search_schedule(
        units,
        candidate_map,
        class_busy,
        teacher_busy,
        assignments,
    ):
        raise TimetableGenerationError(
            "The timetable could not be completely generated. "
            "There are not enough conflict-free periods to satisfy "
            "all active timetable requirements."
        )

    with transaction.atomic():
        entries = [
            TimetableEntry(
                timetable=timetable,
                requirement=assignment["requirement"],
                day=assignment["day"],
                period=assignment["period"],
            )
            for assignment in assignments
        ]

        TimetableEntry.objects.bulk_create(entries)

    return entries