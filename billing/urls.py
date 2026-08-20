from django.urls import path
from . import views

urlpatterns = [
    path("", views.billing_dashboard, name="billing_dashboard"),
    path('pay/<int:student_id>/<int:term_id>/', views.record_payment, name='record_payment'),
    path('owing/', views.students_owing, name='students_owing'),
    path(
        "students-owing/print/",
        views.students_owing_print,
        name="students_owing_print",
    ),
    path('opening-balance/', views.add_opening_balance, name='add_opening_balance'),
    path("opening-balances/", views.opening_balance_list, name="opening_balance_list",),
    path('bill/', views.select_student_bill, name='select_student_bill'),
    path('bill/<int:student_id>/<int:term_id>/', views.student_bill, name='student_bill'),
    path('bill/<int:student_id>/<int:term_id>/pdf/', views.student_bill_pdf, name='student_bill_pdf'),
    path('bill/class/<int:class_id>/<int:term_id>/pdf/', views.class_bill_pdf, name='class_bill_pdf'),
    path("opening-balance/edit/<int:balance_id>/", views.edit_opening_balance, name="edit_opening_balance",),
    path("opening-balance/delete/<int:balance_id>/", views.delete_opening_balance, name="delete_opening_balance",),
    path(
        "opening-balance/pay/<int:balance_id>/",
        views.pay_opening_balance,
        name="pay_opening_balance",
    ),
    path("payments/", views.payment_list, name="payment_list",),
    path("payment/<int:payment_id>/receipt/", views.payment_receipt, name="payment_receipt",),
    path("payment/<int:payment_id>/receipt/pdf/", views.payment_receipt_pdf, name="payment_receipt_pdf",),
    path("student/<int:student_id>/payments/", views.student_payment_history, name="student_payment_history"),
    path("student/<int:student_id>/statement/", views.student_account_statement, name="student_account_statement"),
    path(
        "student/statement/",
        views.select_student_account_statement,
        name="select_student_account_statement",
    ),
    path("my-payments/", views.my_payment_history, name="my_payment_history",),
    path("my-payment/<int:payment_id>/receipt/pdf/", views.my_payment_receipt_pdf, name="my_payment_receipt_pdf",),
    path('students-by-class/', views.students_by_class, name='students_by_class'),
    path(
        "terms-by-session/",
        views.terms_by_session,
        name="terms_by_session",
    ),
    
    path(
        "fee-categories/",
        views.fee_category_list,
        name="fee_category_list",
    ),

    path(
        "fee-categories/add/",
        views.add_fee_category,
        name="add_fee_category",
    ),

    path(
        "fee-categories/<int:category_id>/edit/",
        views.edit_fee_category,
        name="edit_fee_category",
    ),

    path(
        "fee-categories/<int:category_id>/toggle/",
        views.toggle_fee_category,
        name="toggle_fee_category",
    ),
    
    path(
        "fee-assignments/",
        views.fee_assignment_list,
        name="fee_assignment_list",
    ),
    
    path(
        "fee-assignments/student-search/",
        views.fee_assignment_student_search,
        name="fee_assignment_student_search",
    ),

    path(
        "fee-assignments/add/",
        views.add_fee_assignment,
        name="add_fee_assignment",
    ),
    
    path(
        "fee-assignments/<int:assignment_id>/edit/",
        views.edit_fee_assignment,
        name="edit_fee_assignment",
    ),
    
    path(
        "fee-assignments/<int:assignment_id>/students/",
        views.manage_optional_fee_students,
        name="manage_optional_fee_students",
    ),
    
    path(
        "fee-assignments/terms/",
        views.fee_assignment_terms,
        name="fee_assignment_terms",
    ),
    
    path(
        "opening-balance/<int:balance_id>/payments/",
        views.opening_balance_payment_history,
        name="opening_balance_payment_history",
    ),

    path(
        "opening-balance/payment/<int:payment_id>/receipt/",
        views.opening_balance_payment_receipt,
        name="opening_balance_payment_receipt",
    ),

    path(
        "opening-balance/payment/<int:payment_id>/receipt/pdf/",
        views.opening_balance_payment_receipt_pdf,
        name="opening_balance_payment_receipt_pdf",
    ),
]
