from django.urls import path

from . import views


urlpatterns = [
    path("create/", views.create_timetable, name="create_timetable"),
    path("", views.timetable_list, name="timetable_list"),
    
    path(
        "<int:timetable_id>/edit/",
        views.edit_timetable,
        name="edit_timetable",
    ),
    
    path(
        "<int:timetable_id>/view/",
        views.timetable_view,
        name="timetable_view",
    ),

    path(
        "<int:timetable_id>/periods/",
        views.timetable_periods,
        name="timetable_periods",
    ),
    
    path(
        "<int:timetable_id>/requirements/",
        views.timetable_requirements,
        name="timetable_requirements",
    ),
    
    path(
        "<int:timetable_id>/requirements/sync/",
        views.sync_timetable_requirements_view,
        name="sync_timetable_requirements",
    ),
    
    path(
        "<int:timetable_id>/generate/",
        views.generate_timetable_view,
        name="generate_timetable",
    ),
    
    path(
        "<int:timetable_id>/requirements/<int:requirement_id>/edit/",
        views.edit_timetable_requirement,
        name="edit_timetable_requirement",
    ),
    
    path(
        "<int:timetable_id>/requirements/<int:requirement_id>/delete/",
        views.delete_timetable_requirement,
        name="delete_timetable_requirement",
    ),

    path(
        "<int:timetable_id>/periods/<int:period_id>/edit/",
        views.edit_timetable_period,
        name="edit_timetable_period",
    ),

    path(
        "<int:timetable_id>/periods/<int:period_id>/delete/",
        views.delete_timetable_period,
        name="delete_timetable_period",
    ),
    
    path(
        "teacher-availability/",
        views.teacher_availability,
        name="teacher_availability",
    ),
    
    path(
        "teacher-availability/<int:availability_id>/edit/",
        views.edit_teacher_availability,
        name="edit_teacher_availability",
    ),
    path(
        "teacher-availability/<int:availability_id>/delete/",
        views.delete_teacher_availability,
        name="delete_teacher_availability",
    ),
]