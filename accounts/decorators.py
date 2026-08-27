from functools import wraps
from schools.utils import school_has_feature

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
    is_bursar,
    is_platform_admin,
)

from .permissions import can_manage_billing
from .utils import school_subscription_access_allowed


def subscription_required(view_func):
    """
    Restrict school users whose subscription has expired.

    Platform administrators are unrestricted because they operate
    at the Paul SchoolHub platform level rather than under a school
    subscription.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # ---------------------------------------------------------
        # PLATFORM ADMINISTRATORS
        # ---------------------------------------------------------

        if is_platform_admin(request.user):
            return view_func(request, *args, **kwargs)

        # ---------------------------------------------------------
        # SCHOOL USER
        # ---------------------------------------------------------

        school = getattr(request.user, "school", None)

        if not school:
            raise PermissionDenied(
                "Your account is not associated with a school."
            )

        # ---------------------------------------------------------
        # SUBSCRIPTION ACCESS
        # ---------------------------------------------------------

        if not school_subscription_access_allowed(school):
            raise PermissionDenied(
                "Your school's subscription has expired or is inactive. "
                "Please contact your school administrator."
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def platform_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_platform_admin(request.user):
            raise PermissionDenied(
                "Only Paul SchoolHub platform administrators can access this page."
            )
        return view_func(request, *args, **kwargs)

    return wrapper

def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_staff_member(request.user):
            raise PermissionDenied(
                "You do not have permission to access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_teacher(request.user):
            raise PermissionDenied(
                "Only teachers can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def class_teacher_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_class_teacher(request.user):
            raise PermissionDenied(
                "Only class teachers can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def management_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_management(request.user):
            raise PermissionDenied(
                "Only school management can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_admin(request.user):
            raise PermissionDenied(
                "Only administrators can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def proprietoress_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_proprietoress(request.user):
            raise PermissionDenied(
                "Only the proprietoress can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper
    
def principal_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_principal(request.user):
            raise PermissionDenied(
                "Only the principal can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not is_student(request.user):
            raise PermissionDenied(
                "Only students can access this page."
            )

        return subscription_required(view_func)(
            request,
            *args,
            **kwargs
        )

    return wrapper



def billing_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        # Platform administrators have unrestricted
        # platform-level access.
        if is_platform_admin(request.user):
            return view_func(request, *args, **kwargs)

        # Existing school-role billing permission.
        if not can_manage_billing(request.user):
            raise PermissionDenied(
                "You do not have permission to access billing."
            )

        # User must belong to a school.
        school = getattr(request.user, "school", None)

        if not school:
            raise PermissionDenied(
                "Your account is not linked to a school."
            )

        # Check whether the school's subscription
        # includes the Billing feature.
        if not school_has_feature(school, "BILLING"):
            raise PermissionDenied(
                "Billing is not available on your school's "
                "current subscription package."
            )

        return view_func(request, *args, **kwargs)

    return wrapper

def feature_required(feature_code):
    """
    Restrict access to a feature based on the school's
    active subscription package.

    The user's school must have the requested feature.
    """

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                raise PermissionDenied(
                    "You must be logged in to access this feature."
                )

            school = request.user.school

            if not school:
                raise PermissionDenied(
                    "Your account is not associated with a school."
                )

            if not school_has_feature(school, feature_code):
                raise PermissionDenied(
                    "Your school's subscription package does not "
                    "include this feature."
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator