from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='dashboard_home'),
    path('academic/', views.academic_management, name='academic_management'),
    path(
        'academic/department/create/',
        views.create_department,
        name='create_department',
    ),
    path(
        'academic/department/<int:department_id>/edit/',
        views.edit_department,
        name='edit_department',
    ),
    path('academic/session/create/', views.create_academic_session, name='create_academic_session',),
    path('academic/session/<int:session_id>/set-current/', views.set_current_session, name='set_current_session',),
    path('academic/term/create/', views.create_term, name='create_term',),
    path('academic/term/<int:term_id>/set-current/', views.set_current_term, name='set_current_term',),
]