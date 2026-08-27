from django.utils import timezone

from schools.utils import get_school_subscription, is_subscription_expired

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


def get_current_term(user=None):
    """
    Returns the current term for the user's school.
    """
    if not user or not user.is_authenticated or not user.school:
        return None

    return Term.objects.filter(
        session__school=user.school,
        is_current=True
    ).first()


def is_management_user(user):
    """
    True for school administrators/management users.

    ADMIN is the fundamental system-level school management role.
    Additional management positions such as Principal,
    Proprietoress, Vice Principal, etc. are represented
    through SchoolRole.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if user.role == user.Role.ADMIN:
        return True

    school_role = getattr(user, "school_role", None)

    if school_role:
        management_role_names = {
            "principal",
            "proprietoress",
            "vice principal",
            "headmaster",
            "headmistress",
            "school manager",
        }

        return (
            school_role.name.strip().lower()
            in management_role_names
        )

    return False


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



def school_subscription_access_allowed(school):
    """
    Determine whether a school is currently allowed to access
    Paul SchoolHub.

    Access is based on the school's subscription status and
    subscription end date.

    Returns:
        True  -> school can access the system
        False -> school access should be blocked
    """

    if not school:
        return False

    subscription = get_school_subscription(school)

    if not subscription:
        return False

    if not subscription.is_active:
        return False

    if is_subscription_expired(subscription):
        return False

    return True


def get_school_subscription_status(school):
    """
    Return the current subscription status for a school.

    Possible values:

        ACTIVE
        EXPIRING_SOON
        EXPIRED
    """

    from schools.utils import get_subscription_status

    subscription = get_school_subscription(school)

    return get_subscription_status(subscription)
