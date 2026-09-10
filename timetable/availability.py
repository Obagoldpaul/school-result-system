from datetime import time

from .models import TeacherAvailability


def teacher_is_available(teacher, day, start_time, end_time):
    """
    Return True when the teacher is available for the requested
    timetable period.

    If the teacher has no availability records at all, treat the
    teacher as full-time and available for all timetable periods.

    If availability records exist, the requested period must be fully
    contained within one of the teacher's availability windows.
    """

    if not start_time or not end_time or start_time >= end_time:
        return False

    has_availability = TeacherAvailability.objects.filter(
        teacher=teacher,
    ).exists()

    if not has_availability:
        return True

    return TeacherAvailability.objects.filter(
        teacher=teacher,
        day=day,
        start_time__lte=start_time,
        end_time__gte=end_time,
    ).exists()