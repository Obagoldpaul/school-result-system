from allocations.models import SubjectAllocation


# ----------------------------
# Role Checks
# ----------------------------

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


def can_approve_scores(user):
    return is_management(user)


def can_publish_scores(user):
    return is_management(user)


# ----------------------------
# Object Permissions
# ----------------------------

def can_edit_allocation(user, allocation):
    """
    Can this user edit this particular allocation?
    """

    if is_management(user):
        return True

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        allocation.teacher_id == teacher.id
        and allocation.status == SubjectAllocation.Status.DRAFT
    )


def can_review_allocation(user, allocation):

    if is_management(user):
        return True

    teacher = getattr(user, "teacher_profile", None)

    if teacher is None:
        return False

    return (
        teacher.is_class_teacher
        and teacher.assigned_class_id == allocation.school_class_id
    )


def can_view_report(user, student):

    if is_management(user):
        return True

    student_profile = getattr(user, "student_profile", None)

    if student_profile:
        return student_profile.id == student.id

    teacher = getattr(user, "teacher_profile", None)

    if teacher:

        return (
            teacher.is_class_teacher
            and teacher.assigned_class_id == student.school_class_id
        )

    return False