from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_teacher, name="register_teacher"),
    path("edit/<int:teacher_id>/", views.edit_teacher, name="edit_teacher"),
    path("profile/<int:teacher_id>/", views.teacher_profile, name="teacher_profile"),
    path("", views.teacher_list, name="teacher_list"),
]