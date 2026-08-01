from .permissions import (
    is_admin,
    is_principal,
    is_teacher,
    is_class_teacher,
    is_student,
    is_management,
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
    }