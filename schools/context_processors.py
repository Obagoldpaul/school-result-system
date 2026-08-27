
from accounts.permissions import is_platform_admin
from .models import PlatformSettings


def platform_settings(request):
    """
    Make the global Paul SchoolHub platform settings
    available to all templates.
    """

    settings = PlatformSettings.objects.first()

    return {
        "platform_settings": settings,
    }


def platform_context(request):
    """
    Makes platform administrator status and platform settings
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