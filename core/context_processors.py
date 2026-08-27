from schools.models import PlatformSettings
from academics.models import SchoolSettings


def school_settings(request):

    if not request.user.is_authenticated:
        return {
            "school_settings": None
        }

    if not request.user.school:
        return {
            "school_settings": None
        }

    try:
        settings = SchoolSettings.load(
            request.user.school
        )
    except SchoolSettings.DoesNotExist:
        settings = None

    return {
        "school_settings": settings
    }
    
def platform_settings(request):

    settings, created = PlatformSettings.objects.get_or_create(
        pk=1
    )

    return {
        "platform_settings": settings
    }

from accounts.permissions import is_platform_admin
from schools.models import PlatformSettings


def platform_context(request):
    """
    Makes platform branding and platform-admin status
    available globally to templates.
    """

    if not request.user.is_authenticated:
        return {
            "is_platform_admin": False,
            "platform_settings": None,
        }

    try:
        platform_settings = PlatformSettings.objects.get(pk=1)
    except PlatformSettings.DoesNotExist:
        platform_settings = None

    return {
        "is_platform_admin": is_platform_admin(request.user),
        "platform_settings": platform_settings,
    }