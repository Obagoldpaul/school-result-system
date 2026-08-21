from django.urls import path
from . import views


urlpatterns = [
    path(
        "",
        views.platform_dashboard,
        name="platform_dashboard",
    ),

    path(
        "schools/create/",
        views.create_school,
        name="create_school",
    ),
    
    path(
        "schools/<int:school_id>/subscription/edit/",
        views.edit_subscription,
        name="edit_subscription",
    ),

]