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
        and (
            user.is_superuser
            or user.role == user.Role.ADMIN
        )
    )


def has_school_role(user, role_name):
    """
    Check whether the user has a specific active SchoolRole.

    School-specific positions such as Principal, Bursar,
    Vice Principal, Headmaster, etc. are managed through
    SchoolRole rather than User.Role.
    """

    if not user.is_authenticated:
        return False

    school_role = getattr(user, "school_role", None)

    if not school_role:
        return False

    return (
        school_role.is_active
        and school_role.school_id == user.school_id
        and school_role.name.strip().lower()
        == role_name.strip().lower()
    )


def is_proprietoress(user):
    return has_school_role(
        user,
        "Proprietoress",
    )


def is_principal(user):
    return has_school_role(
        user,
        "Principal",
    )


def is_teacher(user):
    return (
        user.is_authenticated
        and user.role == user.Role.TEACHER
    )


def is_class_teacher(user):
    if not user.is_authenticated:
        return False

    teacher = getattr(
        user,
        "teacher_profile",
        None,
    )

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
    return has_school_role(
        user,
        "Bursar",
    )

# ----------------------------
# School Status
# ----------------------------

def is_school_active(user):
    """
    Check whether the user's school is currently active.

    Platform administrators are not restricted by school status.
    """

    if not user.is_authenticated:
        return False

    # Platform administrators operate at platform level.
    if is_platform_admin(user):
        return True

    school = getattr(user, "school", None)

    if school is None:
        return False

    return school.is_active


def school_active_required(view_func):
    """
    Restrict access to users whose school is active.

    Platform administrators bypass this restriction.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        if is_platform_admin(request.user):
            return view_func(request, *args, **kwargs)

        if not is_school_active(request.user):
            messages.error(
                request,
                "Your school account is currently inactive. "
                "Please contact the platform administrator."
            )
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapper
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
        return user_has_permission(
            user,
            "scores.change_score",
        )

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
    return user_has_permission(
        user,
        "reports.principal_remark",
    )

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


from functools import wraps

from django.core.exceptions import PermissionDenied

def user_has_permission(user, permission_name):
    """
    Check whether a user has a specific permission
    through their assigned SchoolRole.
    """

    if not user or not user.is_authenticated:
        return False

    # Platform administrators have unrestricted access.
    if user.role == user.Role.PLATFORM_ADMIN:
        return True

    # User must belong to a school.
    if not user.school_id:
        return False

    # User must have a school role.
    school_role = getattr(user, "school_role", None)

    if not school_role:
        return False

    # Role must be active.
    if not school_role.is_active:
        return False

    # Role must belong to the same school.
    if school_role.school_id != user.school_id:
        return False

    # Check permission assigned to the role.
    return school_role.permissions.filter(
        code=permission_name,
        is_active=True,
    ).exists()



def school_permission_required(permission_codename):
    """
    Decorator for views that require a specific SchoolRole permission.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):

            if not user_has_permission(
                request.user,
                permission_codename,
            ):
                raise PermissionDenied

            return view_func(
                request,
                *args,
                **kwargs,
            )

        return wrapped_view

    return decorator