from django.core.exceptions import PermissionDenied
from accounts.permissions import can_view_report, can_edit_allocation as _can_edit_allocation
from allocations.models import SubjectAllocation
from .models import get_cumulative_report_rows, get_class_results


def build_report_card_context(student, term):
    from academics.models import SchoolSettings

    cumulative_rows, relevant_terms = get_cumulative_report_rows(student, term)

    current_term_total = sum(
        row['ca_score'] + row['exam_score']
        for row in cumulative_rows if row['ca_score'] != '-'
    )
    subject_count = len(cumulative_rows)
    marks_obtainable = subject_count * 100
    percentage = round((current_term_total / marks_obtainable) * 100, 1) if marks_obtainable else 0
    overall_percentage = round(
        sum(r['average'] for r in cumulative_rows) / len(cumulative_rows), 1
    ) if cumulative_rows else 0

    class_results = get_class_results(student.school_class, term)
    position = next((r['position'] for r in class_results if r['student'].id == student.id), '-')

    return {
        'cumulative_rows': cumulative_rows,
        'relevant_terms': relevant_terms,
        'total': current_term_total,
        'marks_obtainable': marks_obtainable,
        'percentage': percentage,
        'overall_percentage': overall_percentage,
        'position': position,
        'school_settings': SchoolSettings.objects.first(),
    }


def check_report_card_access(user, student, term):
    from .models import is_class_term_fully_published
    if not can_view_report(user, student):
        raise PermissionDenied("You do not have permission to view this report card.")

    from accounts.permissions import is_student
    if is_student(user) and not is_class_term_fully_published(student.school_class, term):
        raise PermissionDenied("This term's results have not been fully published yet.")


def check_allocation_ownership(user, allocation):
    if not _can_edit_allocation(user, allocation) and allocation.status != SubjectAllocation.Status.DRAFT:
        # allow view access even if not editable; real edit-lock happens in can_edit_allocation below
        pass
    from accounts.permissions import is_management
    teacher = getattr(user, "teacher_profile", None)
    if teacher and allocation.teacher_id != teacher.id and not is_management(user):
        raise PermissionDenied("You are not assigned to teach this subject/class.")


def can_edit_allocation(user, allocation):
    return _can_edit_allocation(user, allocation) or user.is_superuser


def submit_allocation_for_review(allocation, user=None):
    if allocation.status == SubjectAllocation.Status.DRAFT:
        allocation.status = SubjectAllocation.Status.SUBMITTED
        allocation.save()
        from activitylog.models import log_activity
        log_activity(user, f"{allocation.teacher} submitted {allocation.subject} - {allocation.school_class}")


def mark_allocation_reviewed(allocation, comment, user=None):
    allocation.class_teacher_comment = comment
    if allocation.status == SubjectAllocation.Status.SUBMITTED:
        allocation.status = SubjectAllocation.Status.REVIEWED
        from activitylog.models import log_activity
        log_activity(user, f"{user} reviewed {allocation.subject} - {allocation.school_class}")
    allocation.save()


def approve_allocation_results(allocation, user=None):
    if allocation.status == SubjectAllocation.Status.REVIEWED:
        allocation.status = SubjectAllocation.Status.APPROVED
        allocation.save()
        from activitylog.models import log_activity
        log_activity(user, f"{user} approved {allocation.subject} - {allocation.school_class}")


def publish_allocation_results(allocation, user=None):
    if allocation.status == SubjectAllocation.Status.APPROVED:
        allocation.status = SubjectAllocation.Status.PUBLISHED
        allocation.save()
        from activitylog.models import log_activity
        log_activity(user, f"{user} published {allocation.subject} - {allocation.school_class}")