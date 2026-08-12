from django.core.exceptions import PermissionDenied
from accounts.permissions import can_view_report, can_edit_allocation as _can_edit_allocation
from allocations.models import SubjectAllocation
from .reports import get_cumulative_report_rows, get_class_results
from students.models import Student
from .models import Score
from .exceptions import ScoreValidationError




def build_report_card_context(student, term):
    from academics.models import SchoolSettings
    from attendance.models import get_attendance_summary

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
    
    days_present, days_school_opened = get_attendance_summary(
    student,
    term
    )

    days_absent = (
        days_school_opened - days_present
        if days_present is not None and days_school_opened is not None
        else None
    )

    return {
    'cumulative_rows': cumulative_rows,
    'relevant_terms': relevant_terms,
    'total': current_term_total,
    'marks_obtainable': marks_obtainable,
    'percentage': percentage,
    'overall_percentage': overall_percentage,
    'school_settings': SchoolSettings.load(
        student.user.school
    ),
    
    'days_present': days_present,
    'days_school_opened': days_school_opened,
    'days_absent': days_absent,
    }


def check_report_card_access(user, student, term):
    from .models import is_class_term_fully_published

    if not can_view_report(user, student):
        raise PermissionDenied(
            "You do not have permission to view this report card."
        )

    if student.school_class.school_id != term.session.school_id:
        raise PermissionDenied(
            "The student and academic term must belong to the same school."
        )

    from accounts.permissions import is_student

    if is_student(user) and not is_class_term_fully_published(
        student.school_class,
        term,
    ):
        raise PermissionDenied(
            "This term's results have not been fully published yet."
        )


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


def get_students_for_allocation(allocation):
    """
    Returns the students that should receive scores for a subject allocation.
    Handles elective subjects automatically.
    """
    students = Student.objects.filter(
        school_class=allocation.school_class,
        is_active=True
    )

    if allocation.subject.is_elective:
        students = students.filter(
            elective_subjects=allocation.subject
        )

    return students


def save_scores(allocation, students, post_data):
    """
    Saves scores entered for all students in an allocation.
    Validates CA and Exam scores before saving.
    """

    for student in students:

        ca = post_data.get(f"ca_{student.id}", "").strip()
        exam = post_data.get(f"exam_{student.id}", "").strip()

        if not ca and not exam:
            continue

        try:
            ca_value = float(ca or 0)
            exam_value = float(exam or 0)

        except ValueError:
            raise ScoreValidationError(
                f"Invalid score entered for {student}."
            )

        if ca_value < 0 or ca_value > 40:
            raise ScoreValidationError(
                f"CA score for {student} must be between 0 and 40."
            )

        if exam_value < 0 or exam_value > 60:
            raise ScoreValidationError(
                f"Exam score for {student} must be between 0 and 60."
            )

        score, created = Score.objects.update_or_create(
            student=student,
            subject=allocation.subject,
            term=allocation.term,
            defaults={
                "ca_score": ca_value,
                "exam_score": exam_value,
                "recorded_by": allocation.teacher,
            },
        )

        score.full_clean()
        score.save()


def get_student_score_pairs(allocation, students):
    """
    Returns students paired with their existing scores for an allocation.
    """

    existing_scores = {
        score.student_id: score
        for score in Score.objects.filter(
            subject=allocation.subject,
            term=allocation.term,
            student__in=students
        )
    }

    return [
        (student, existing_scores.get(student.id))
        for student in students
    ]


def ensure_can_submit(user, allocation):
    if allocation.status != SubjectAllocation.Status.DRAFT:
        raise PermissionDenied(
            "Only Draft results can be submitted."
        )

    check_allocation_ownership(user, allocation)

def ensure_can_review(user, allocation):
    from accounts.permissions import can_review_allocation

    if not can_review_allocation(user, allocation):
        raise PermissionDenied(
            "You cannot review these results."
        )

    if allocation.status != SubjectAllocation.Status.SUBMITTED:
        raise PermissionDenied(
            "Only Submitted results can be reviewed."
        )

def ensure_can_approve(user, allocation):
    from accounts.permissions import can_approve_scores

    if not can_approve_scores(user):
        raise PermissionDenied(
            "You cannot approve results."
        )

    if allocation.status != SubjectAllocation.Status.REVIEWED:
        raise PermissionDenied(
            "Only Reviewed results can be approved."
        )

def ensure_can_publish(user, allocation):
    from accounts.permissions import can_publish_scores

    if not can_publish_scores(user):
        raise PermissionDenied(
            "You cannot publish results."
        )

    if allocation.status != SubjectAllocation.Status.APPROVED:
        raise PermissionDenied(
            "Only Approved results can be published."
        )

