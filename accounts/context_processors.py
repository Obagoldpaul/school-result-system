from .permissions import (
    is_admin,
    is_principal,
    is_teacher,
    is_class_teacher,
    is_student,
    is_management,
    can_manage_billing,
)


def user_roles(request):
    user = request.user

    if not user.is_authenticated:
        return {}

    return {
        "is_admin": is_admin(user),
        "is_principal": is_principal(user),
        "is_management": is_management(user),
        "is_teacher": is_teacher(user),
        "is_class_teacher": is_class_teacher(user),
        "is_student": is_student(user),
        "can_manage_billing": can_manage_billing(user),
    }


def announcements_preview(request):
    if not request.user.is_authenticated:
        return {}

    from announcements.models import get_announcements_for_user
    recent = list(get_announcements_for_user(request.user, limit=5))
    return {
        'nav_announcements': recent,
        'nav_announcement_count': len(recent),
    }
    