from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_student, name='register_student'),
    path('edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('promote/', views.promote_class, name='promote_class'),
    path('class-management/', views.class_management, name='class_management'),
    path('class-management/add/', views.add_class, name='add_class'),
    path('class-management/<int:class_id>/edit/', views.edit_class, name='edit_class'),
    path('', views.student_list, name='student_list'),
    path("profile/<int:student_id>/", views.student_profile, name="student_profile"),
]