from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_allocation, name='select_allocation'),
    path('enter/<int:allocation_id>/', views.enter_scores, name='enter_scores'),
    path('submit/<int:allocation_id>/', views.submit_allocation, name='submit_allocation'),
    path('review/<int:allocation_id>/', views.review_allocation, name='review_allocation'),
    path('approve/<int:allocation_id>/', views.approve_allocation, name='approve_allocation'),
    path('publish/<int:allocation_id>/', views.publish_allocation, name='publish_allocation'),
    path('results/', views.class_results, name='class_results'),
    path('report/<int:student_id>/', views.select_report_term, name='select_report_term'),
    path('report/<int:student_id>/<int:term_id>/', views.report_card, name='report_card'),
    path('report/<int:student_id>/<int:term_id>/edit/', views.edit_report_extra, name='edit_report_extra'),
    path('report/<int:student_id>/<int:term_id>/pdf/', views.report_card_pdf, name='report_card_pdf'),
]