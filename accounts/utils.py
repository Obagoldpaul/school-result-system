from academics.models import Term


def get_teacher(user):
    """
    Returns the Teacher profile for a user,
    or None if the user is not a teacher.
    """
    return getattr(user, "teacher_profile", None)


def get_student(user):
    """
    Returns the Student profile for a user,
    or None if the user is not a student.
    """
    return getattr(user, "student_profile", None)


def get_current_term():
    """
    Returns the active school term.
    """
    return Term.objects.filter(is_current=True).first()


def is_management_user(user):
    """
    True for Admins, Principals and Superusers.
    """
    from .models import User

    return (
        user.is_authenticated and
        (
            user.is_superuser or
            user.role in [
                User.Role.ADMIN,
                User.Role.PRINCIPAL,
            ]
        )
    )


def is_teacher(user):
    """
    True if the user has a teacher profile.
    """
    return hasattr(user, "teacher_profile")


def is_student(user):
    """
    True if the user has a student profile.
    """
    return hasattr(user, "student_profile")


def is_class_teacher(user):
    """
    True if the teacher is assigned as a class teacher.
    """
    teacher = get_teacher(user)

    if teacher:
        return teacher.is_class_teacher

    return False