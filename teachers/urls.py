from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_teacher, name="register_teacher"),

    path("profile/<int:teacher_id>/", views.teacher_profile, name="teacher_profile"),

    path("edit/<int:teacher_id>/", views.edit_teacher, name="edit_teacher"),

    path("deactivate/<int:teacher_id>/", views.deactivate_teacher, name="deactivate_teacher"),

    path("activate/<int:teacher_id>/", views.activate_teacher, name="activate_teacher"),

    path("print/<int:teacher_id>/", views.print_teacher_profile, name="print_teacher_profile"),

    path("", views.teacher_list, name="teacher_list"),
]