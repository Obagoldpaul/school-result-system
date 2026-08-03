from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_student, name='register_student'),
    path('edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('promote/', views.promote_class, name='promote_class'),
    path('', views.student_list, name='student_list'),
]