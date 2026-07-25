from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_subject, name='add_subject'),
    path('', views.subject_list, name='subject_list'),
    path('assign/', views.assign_subject_to_class, name='assign_subject_to_class'),
    path('class-subjects/', views.class_subject_list, name='class_subject_list'),
]