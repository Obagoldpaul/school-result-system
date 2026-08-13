from django.urls import path

from . import views


urlpatterns = [
    path(
        "settings/",
        views.school_settings,
        name="school_settings",
    ),
]