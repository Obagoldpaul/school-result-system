from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from accounts.permissions import is_platform_admin

from .models import MaintenanceMode


class MaintenanceMiddleware:
    """
    Redirect non-platform users to the maintenance page
    while global maintenance mode is enabled.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        maintenance = MaintenanceMode.get_solo()

        if not maintenance.is_enabled:
            return self.get_response(request)

        maintenance_url = reverse("maintenance_status")

        allowed_paths = {
            maintenance_url,
            reverse("login"),
            reverse("platform_login"),
        }

        if request.path in allowed_paths:
            return self.get_response(request)

        if request.path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        if request.path.startswith(settings.MEDIA_URL):
            return self.get_response(request)

        if (
            request.user.is_authenticated
            and is_platform_admin(request.user)
        ):
            return self.get_response(request)

        return redirect("maintenance_status")