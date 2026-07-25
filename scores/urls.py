from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_allocation, name='select_allocation'),
    path('enter/<int:allocation_id>/', views.enter_scores, name='enter_scores'),
    path('results/', views.class_results, name='class_results'),
    path('report/<int:student_id>/<int:term_id>/', views.report_card, name='report_card'),
    path('report/<int:student_id>/<int:term_id>/edit/', views.edit_report_extra, name='edit_report_extra'),
]