from functools import wraps

from django.core.exceptions import PermissionDenied

from .permissions import (
    is_staff_member,
    is_teacher,
    is_class_teacher,
    is_management,
    is_admin,
    is_principal,
    is_student,
    is_proprietoress,
    is_bursar
)

from .permissions import can_manage_billing

def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_staff_member(request.user):
            raise PermissionDenied("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_teacher(request.user):
            raise PermissionDenied("Only teachers can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def class_teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_class_teacher(request.user):
            raise PermissionDenied("Only class teachers can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def management_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_management(request.user):
            raise PermissionDenied("Only school management can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Only administrators can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def proprietoress_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_proprietoress(request.user):
            raise PermissionDenied(
                "Only the proprietoress can access this page."
            )
        return view_func(request, *args, **kwargs)
    return wrapper
    
def principal_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_principal(request.user):
            raise PermissionDenied("Only the principal can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_student(request.user):
            raise PermissionDenied("Only students can access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper



def billing_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not can_manage_billing(request.user):
            raise PermissionDenied(
                "You do not have permission to access billing."
            )

        return view_func(request, *args, **kwargs)

    return wrapper