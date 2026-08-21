from allocations.models import SubjectAllocation

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from schools.utils import school_has_feature

# ----------------------------
# Role Checks
# ----------------------------
def is_platform_admin(user):
    return (
        user.is_authenticated
        and user.role == user.Role.PLATFORM_ADMIN
    )

def is_admin(user):
    return (
        user.is_authenticated
        and (user.is_superuser or user.role == user.Role.ADMIN)
    )

def is_proprietoress(user):
    return (
        user.is_authenticated
        and user.role == user.Role.PROPRIETORESS
    )

def is_principal(user):
    return (
        user.is_authenticated
        and user.role == user.Role.PRINCIPAL
    )


def is_teacher(user):
    return (
        user.is_authenticated
        and user.role == user.Role.TEACHER
    )


def is_class_teacher(user):
    if not user.is_authenticated:
        return False

    teacher = getattr(user, "teacher_profile", None)

    return (
        teacher is not None
        and teacher.is_class_teacher
    )


def is_student(user):
    return (
        user.is_authenticated
        and user.role == user.Role.STUDENT
    )


def is_management(user):
    return (
        is_admin(user)
        or is_principal(user)
        or is_proprietoress(user)
    )


def is_staff_member(user):
    return (
        is_management(user)
        or is_teacher(user)
    )

def is_bursar(user):
    return (
        user.is_authenticated
        and user.role == user.Role.BURSAR
    )

# ----------------------------
# Workflow Permissions
# ----------------------------

def can_enter_scores(user):
    return (
        is_teacher(user)
        or is_management(user)
    )


def can_submit_scores(user):
    return (
        is_teacher(user)
        or is_management(user)
    )


def can_review_scores(user):
    return (
        is_class_teacher(user)
        or is_management(user)
    )


def can_approve_scores(user, allocation=None):
    if not user.is_authenticated or not user.school:
        return False

    if not is_management(user):
        return False

    if allocation is not None:
        return (
            allocation.school_class.school_id
            == user.school_id
        )

    return True


def can_publish_scores(user, allocation=None):
    if not user.is_authenticated or not user.school:
        return False

    if not is_management(user):
        return False

    if allocation is not None:
        return (
            allocation.school_class.school_id
            == user.school_id
        )

    return True


def can_manage_billing(user):
    return (
        is_management(user)
        or is_bursar(user)
    )

# ----------------------------
# Object Permissions
# ----------------------------

def can_edit_allocation(user, allocation):
    """
    Can this user edit this particular allocation?

    An allocation must always belong to the same school
    as the logged-in user.
    """

    if not user.is_authenticated or not user.school:
        return False

    # ==========================
    # MULTI-TENANT SAFETY
    # ==========================

    if allocation.school_class.school_id != user.school_id:
        return False

    # ==========================
    # MANAGEMENT
    # ==========================

    if is_management(user):
        return True

    # ==========================
    # TEACHER
    # ==========================

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        allocation.teacher_id == teacher.id
        and allocation.school_class.school_id == user.school_id
        and allocation.status == SubjectAllocation.Status.DRAFT
    )


def can_review_allocation(user, allocation):

    if not user.is_authenticated or not user.school:
        return False

    # ==========================
    # MULTI-TENANT SAFETY
    # ==========================

    if allocation.school_class.school_id != user.school_id:
        return False

    if is_management(user):
        return True

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        teacher.is_class_teacher
        and teacher.assigned_class_id == allocation.school_class_id
        and teacher.user.school_id == user.school_id
    )


def can_view_report(user, student):
    """
    Can this user view this student's report card?
    """

    if not user.is_authenticated or not user.school:
        return False

    if not student.school_class_id:
        return False

    if student.school_class.school_id != user.school_id:
        return False

    if is_management(user):
        return True

    student_profile = getattr(user, "student_profile", None)

    if student_profile:
        return student_profile.id == student.id

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        teacher.is_class_teacher
        and teacher.assigned_class_id == student.school_class_id
        and teacher.user.school_id == user.school_id
    )

def can_edit_report_extra(user, student):
    """
    Can this user edit the report-card extras for this student?
    """

    if not user.is_authenticated or not user.school:
        return False

    if not student.school_class_id:
        return False

    if student.school_class.school_id != user.school_id:
        return False

    if is_management(user):
        return True

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        teacher.is_class_teacher
        and teacher.assigned_class_id == student.school_class_id
        and teacher.user.school_id == user.school_id
    )


def can_edit_principal_remark(user):
    """
    Can this user edit the principal's remark?
    """

    return is_management(user)

def feature_required(feature_code):
    """
    Restrict access to a view based on the school's
    active subscription package.

    Platform administrators bypass school feature restrictions.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect("login")

            # Platform administrators have access to all features.
            if is_platform_admin(request.user):
                return view_func(request, *args, **kwargs)

            school = getattr(request.user, "school", None)

            if not school:
                messages.error(
                    request,
                    "Your account is not linked to a school."
                )
                return redirect("dashboard_home")

            if not school_has_feature(school, feature_code):
                messages.error(
                    request,
                    "This feature is not available on your school's "
                    "current subscription package."
                )
                return redirect("dashboard_home")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator