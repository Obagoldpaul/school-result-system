from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_class_for_attendance, name='select_class_for_attendance'),
    path('mark/<int:class_id>/', views.mark_attendance, name='mark_attendance'),
    path('summary/', views.class_attendance_summary, name='class_attendance_summary'),
]