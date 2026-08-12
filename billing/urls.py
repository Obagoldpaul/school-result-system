from django.urls import path
from . import views

urlpatterns = [
    path("", views.billing_dashboard, name="billing_dashboard"),
    path('fees/add/', views.add_fee_structure, name='add_fee_structure'),
    path('fees/', views.fee_structure_list, name='fee_structure_list'),
    path('pay/<int:student_id>/<int:term_id>/', views.record_payment, name='record_payment'),
    path('owing/', views.students_owing, name='students_owing'),
    path('opening-balance/', views.add_opening_balance, name='add_opening_balance'),
    path("opening-balances/", views.opening_balance_list, name="opening_balance_list",),
    path('bill/<int:student_id>/<int:term_id>/', views.student_bill, name='student_bill'),
    path('bill/<int:student_id>/<int:term_id>/pdf/', views.student_bill_pdf, name='student_bill_pdf'),
    path('bill/class/<int:class_id>/<int:term_id>/pdf/', views.class_bill_pdf, name='class_bill_pdf'),
    path("opening-balance/edit/<int:balance_id>/", views.edit_opening_balance, name="edit_opening_balance",),
    path("opening-balance/delete/<int:balance_id>/", views.delete_opening_balance, name="delete_opening_balance",),
    path("payments/", views.payment_list, name="payment_list",),
    path("payment/<int:payment_id>/receipt/", views.payment_receipt, name="payment_receipt",),
    path("payment/<int:payment_id>/receipt/pdf/", views.payment_receipt_pdf, name="payment_receipt_pdf",),
    path("student/<int:student_id>/payments/", views.student_payment_history, name="student_payment_history"),
    path('fees/<int:fee_id>/edit/', views.edit_fee_structure, name='edit_fee_structure'),
    path('fees/<int:fee_id>/delete/', views.delete_fee_structure, name='delete_fee_structure'),
    path("fees/<int:fee_id>/students/", views.fee_structure_students, name="fee_structure_students",),
]