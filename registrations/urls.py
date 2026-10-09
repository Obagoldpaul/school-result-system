from django.urls import path

from . import views


urlpatterns = [
    path(
        "applications/",
        views.registration_application_list,
        name="registration_application_list",
    ),
    
    path(
        "applications/<int:application_id>/",
        views.registration_application_detail,
        name="registration_application_detail",
    ),
    
    path(
        "applications/<int:application_id>/approve/",
        views.approve_registration_application,
        name="approve_registration_application",
    ),
    
    path(
        "applications/<int:application_id>/reject/",
        views.reject_registration_application,
        name="reject_registration_application",
    ),
]