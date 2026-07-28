from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def staff_required(view_func):
    """Only allow Admin, Principal, Teacher, or Class Teacher roles. Blocks students."""
    def check(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.role == user.Role.STUDENT:
            raise PermissionDenied("Students are not permitted to access this page.")
        return True

    decorated = user_passes_test(check, login_url='/admin/login/')
    return decorated(view_func)