from django.urls import path

from library import views


urlpatterns = [
    path(
        "lesson-notes/create/",
        views.lesson_note_create,
        name="lesson_note_create",
    ),
    
    path(
        "curriculums/",
        views.curriculum_list,
        name="curriculum_list",
    ),
]