from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_subject, name='add_subject'),
    path('', views.subject_list, name='subject_list'),

    path(
        '<int:subject_id>/edit/',
        views.edit_subject,
        name='edit_subject'
    ),

    path(
        '<int:subject_id>/deactivate/',
        views.deactivate_subject,
        name='deactivate_subject'
    ),

    path(
        '<int:subject_id>/activate/',
        views.activate_subject,
        name='activate_subject'
    ),

    path(
        'assign/',
        views.assign_subject_to_class,
        name='assign_subject_to_class'
    ),

    path(
        'class-subjects/',
        views.class_subject_list,
        name='class_subject_list'
    ),

    path(
        'inactive/',
        views.inactive_subject_list,
        name='inactive_subject_list'
    ),

    path(
        'class-subjects/<int:assignment_id>/unassign/',
        views.unassign_subject_from_class,
        name='unassign_subject_from_class',
    ),
]
