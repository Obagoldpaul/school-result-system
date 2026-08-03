from django.urls import path
from . import views

urlpatterns = [
    path('fees/add/', views.add_fee_structure, name='add_fee_structure'),
    path('fees/', views.fee_structure_list, name='fee_structure_list'),
    path('pay/<int:student_id>/<int:term_id>/', views.record_payment, name='record_payment'),
    path('owing/', views.students_owing, name='students_owing'),
    path('opening-balance/', views.add_opening_balance, name='add_opening_balance'),
    path('bill/<int:student_id>/<int:term_id>/', views.student_bill, name='student_bill'),
    path('bill/<int:student_id>/<int:term_id>/pdf/', views.student_bill_pdf, name='student_bill_pdf'),
    path('bill/class/<int:class_id>/<int:term_id>/pdf/', views.class_bill_pdf, name='class_bill_pdf'),
]