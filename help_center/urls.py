from django.urls import path
from . import views

app_name = "help_center"

urlpatterns = [
    path("", views.help_home, name="home"),
    path("about/", views.about, name="about"),
    path(
        "getting-started/",
        views.getting_started,
        name="getting_started",
    ),
    path(
        "school-administration/",
        views.school_administration,
        name="school_administration",
    ),
    
    path(
        "teaching-academics/",
        views.teaching_academics,
        name="teaching_academics",
    ),
    
    path(
        "fees-payments/",
        views.fees_payments,
        name="fees_payments",
    ),
    
    path(
        "student-parent-portal/",
        views.student_parent_portal,
        name="student_parent_portal",
    ),
]