from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_teacher, name='register_teacher'),
    path('', views.teacher_list, name='teacher_list'),
]