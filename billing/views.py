from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
from accounts.decorators import management_required
from accounts.utils import get_current_term
from students.models import Student, SchoolClass
from academics.models import Term, SchoolSettings
from .forms import FeeStructureForm, PaymentForm, OpeningBalanceForm
from .models import FeeStructure, Payment, OpeningBalance, get_cumulative_balance
from django.db.models import Sum
from django.db.models import Q
from django.db import models
from django.contrib import messages
from accounts.decorators import billing_required
from django.core.exceptions import PermissionDenied



@login_required
@billing_required
def billing_dashboard(request):

    school = request.user.school
    current_term = get_current_term(request.user)

    total_students = Student.objects.filter(
        school_class__school=school,
        is_active=True
    ).count()

    total_fee_structures = FeeStructure.objects.filter(
        school_class__school=school
    ).count()

    total_opening_balances = OpeningBalance.objects.filter(
        student__user__school=school
    ).count()

    total_payments = Payment.objects.filter(
        student__user__school=school
    ).count()

    recent_payments = Payment.objects.select_related(
        "student",
        "student__user",
        "term",
        "recorded_by"
    ).filter(
        student__user__school=school
    ).order_by(
        "-date_paid"
    )[:5]

    total_collected = Payment.objects.filter(
        student__user__school=school
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    expected_revenue = 0
    collection_rate = 0
    students_owing = 0
    outstanding = 0

    if current_term:

        students = Student.objects.filter(
            user__school=school,
            is_active=True
        )

        for student in students:

            fee_amount, total_paid, balance = get_cumulative_balance(
                student,
                current_term
            )

            if balance > 0:

                students_owing += 1
                outstanding += balance

        expected_revenue = total_collected + outstanding

        if expected_revenue > 0:
            collection_rate = (
                total_collected / expected_revenue
            ) * 100

    context = {

        "current_term": current_term,

        "total_students": total_students,

        "total_fee_structures": total_fee_structures,

        "total_opening_balances": total_opening_balances,

        "total_payments": total_payments,

        "total_collected": total_collected,

        "students_owing": students_owing,

        "outstanding": outstanding,

        "expected_revenue": expected_revenue,

        "collection_rate": round(collection_rate, 2),

        "recent_payments": recent_payments,

    }

    return render(
        request,
        "billing/dashboard.html",
        context,
    )

@login_required
@billing_required
def add_fee_structure(request):

    if request.method == "POST":

        form = FeeStructureForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            fee = form.save(commit=False)

            if request.user.is_superuser:
                fee.save()

            else:

                if fee.school_class.school_id != request.user.school_id:
                    raise PermissionDenied(
                        "You cannot create a fee structure "
                        "for another school."
                    )

                if fee.term.session.school_id != request.user.school_id:
                    raise PermissionDenied(
                        "You cannot use a term from another school."
                    )

                if (
                    fee.department
                    and fee.department.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a department from another school."
                    )

                fee.save()

            return redirect(
                "fee_structure_list"
            )

    else:

        form = FeeStructureForm(
            user=request.user,
        )

    return render(
        request,
        "billing/add_fee_structure.html",
        {
            "form": form,
            "fee_structure_list_url": "/billing/fees/",
            "page_title": "Add Fee Structure",
        },
    )

@login_required
@billing_required
def edit_fee_structure(request, fee_id):

    fee = get_object_or_404(
        FeeStructure,
        id=fee_id,
        school_class__school=request.user.school
    )

    if request.method == "POST":

        form = FeeStructureForm(
            request.POST,
            instance=fee,
            user=request.user,
        )

        if form.is_valid():

            updated_fee = form.save(commit=False)

            if request.user.is_superuser:
                updated_fee.save()

            else:

                if (
                    updated_fee.school_class.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot assign a fee structure "
                        "to another school."
                    )

                if (
                    updated_fee.term.session.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a term from another school."
                    )

                if (
                    updated_fee.department
                    and updated_fee.department.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a department from another school."
                    )

                updated_fee.save()

            return redirect(
                "fee_structure_list"
            )

    else:

        form = FeeStructureForm(
            instance=fee,
            user=request.user
        )

    return render(
        request,
        "billing/add_fee_structure.html",
        {
            "form": form,
            "fee_structure_list_url": "/billing/fees/",
            "page_title": "Edit Fee Structure",
        },
    )
    
@login_required
@billing_required
def delete_fee_structure(request, fee_id):

    fee_queryset = FeeStructure.objects.all()

    if not request.user.is_superuser:
        fee_queryset = fee_queryset.filter(
            school_class__school=request.user.school
        )

    fee = get_object_or_404(
        fee_queryset,
        id=fee_id
    )

    # Prevent accidental deletion
    if request.method == "POST":

        success_message = (
            f"Fee structure for {fee.school_class} "
            f"({fee.term}) was deleted successfully."
        )

        fee.delete()

        messages.success(
            request,
            success_message
        )

        return redirect(
            "fee_structure_list"
        )

    return render(
        request,
        "billing/delete_fee_structure.html",
        {
            "fee": fee
        }
    )

@login_required
@billing_required
def fee_structure_list(request):

    fees = FeeStructure.objects.select_related(
        "school_class",
        "department",
        "term"
    )

    if not request.user.is_superuser:
        fees = fees.filter(
            school_class__school=request.user.school
        )

    search = request.GET.get("search", "")

    if search:
        fees = fees.filter(
            school_class__name__icontains=search
        )

    context = {
        "fees": fees,
        "search": search,
        "total_fees": fees.count(),
        "total_classes": fees.values(
            "school_class"
        ).distinct().count(),
        "total_terms": fees.values(
            "term"
        ).distinct().count(),
    }

    return render(
        request,
        "billing/fee_structure_list.html",
        context,
    )
    

@login_required
@billing_required
def fee_structure_students(request, fee_id):

    fee_queryset = FeeStructure.objects.all()

    if not request.user.is_superuser:
        fee_queryset = fee_queryset.filter(
            school_class__school=request.user.school
        )

    fee = get_object_or_404(
        fee_queryset,
        id=fee_id
    )

    students = Student.objects.select_related(
        "user",
        "school_class",
        "department"
    ).filter(
        school_class=fee.school_class,
        user__school=fee.school_class.school,
        is_active=True,
    )

    if fee.department:

        students = students.filter(
            department=fee.department
        )

    else:

        students = students.filter(
            department__isnull=True
        )

    student_records = []

    for student in students:

        total_fee, total_paid, balance = get_cumulative_balance(
            student,
            fee.term
        )

        if balance <= 0:

            status = "Paid"

        elif total_paid > 0:

            status = "Part Payment"

        else:

            status = "Owing"

        student_records.append({

            "student": student,

            "fee": total_fee,

            "paid": total_paid,

            "balance": balance,

            "status": status,

        })

    context = {

        "fee": fee,

        "students": student_records,

        "total_students": len(student_records),

    }

    return render(
        request,
        "billing/fee_structure_students.html",
        context,
    )

@login_required
@billing_required
def record_payment(request, student_id, term_id):

    student_queryset = Student.objects.all()
    term_queryset = Term.objects.all()

    if not request.user.is_superuser:
        student_queryset = student_queryset.filter(
            user__school=request.user.school
        )

        term_queryset = term_queryset.filter(
            session__school=request.user.school
        )

    student = get_object_or_404(
        student_queryset,
        id=student_id
    )

    term = get_object_or_404(
        term_queryset,
        id=term_id
    )
    if student.user.school_id != term.session.school_id:
        raise PermissionDenied(
            "The student and term must belong to the same school."
        )

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            payment.term = term
            payment.recorded_by = request.user
            payment.save()
            return render(request, 'billing/payment_success.html', {
        'payment': payment,
    })
    else:
        form = PaymentForm()

    fee_amount, total_paid, balance = get_cumulative_balance(student, term)

    return render(request, 'billing/record_payment.html', {
        'form': form,
        'student': student,
        'term': term,
        'fee_amount': fee_amount,
        'total_paid': total_paid,
        'balance': balance,
    })


@login_required
@billing_required
def students_owing(request):
    class_id = request.GET.get("class")

    school = request.user.school

    current_term = get_current_term(request.user)

    term_id = request.GET.get("term") or (
        current_term.id if current_term else None
    )

    students = Student.objects.filter(
        user__school=school,
        is_active=True,
    )

    if class_id:
        students = students.filter(
            school_class_id=class_id,
            school_class__school=school,
        )

    rows = []
    term = None

    if term_id:
        term = get_object_or_404(
            Term,
            id=term_id,
            session__school=school,
        )

        for student in students:
            fee_amount, total_paid, balance = get_cumulative_balance(
                student,
                term,
            )

            if balance is not None and balance > 0:
                rows.append({
                    "student": student,
                    "fee_amount": fee_amount,
                    "total_paid": total_paid,
                    "balance": balance,
                })

    return render(
        request,
        "billing/students_owing.html",
        {
            "rows": rows,
            "classes": SchoolClass.objects.filter(
                school=school
            ),
            "terms": Term.objects.filter(
                session__school=school
            ),
            "selected_class": class_id,
            "selected_term": term_id,
            "term": term,
        },
    )


@login_required
@billing_required
def add_opening_balance(request):

    if request.method == 'POST':

        form = OpeningBalanceForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            balance = form.save(commit=False)

            if (
                not request.user.is_superuser
                and balance.student.user.school_id != request.user.school_id
            ):
                raise PermissionDenied(
                    "You cannot create an opening balance for a student "
                    "from another school."
                )

            balance.save()

            return redirect(
                'students_owing'
            )

    else:

        form = OpeningBalanceForm(
            user=request.user
        )

    return render(
        request,
        'billing/add_opening_balance.html',
        {
            'form': form,
            'students_owing_url': '/billing/owing/',
        }
    )


@login_required
@billing_required
def opening_balance_list(request):

    balances = OpeningBalance.objects.select_related(
        "student",
        "student__user"
    ).filter(
        student__user__school=request.user.school
    )

    search = request.GET.get("search", "")

    if search:

        balances = balances.filter(
            Q(student__user__first_name__icontains=search)
            | Q(student__user__last_name__icontains=search)
            | Q(student__admission_number__icontains=search)
        )

    return render(
        request,
        "billing/opening_balance_list.html",
        {
            "balances": balances,
            "search": search,
        }
    )

def _bill_context_for_student(student, term):
    fee_amount, total_paid, balance = get_cumulative_balance(student, term)
    return {
        'student': student,
        'term': term,
        'fee_amount': fee_amount,
        'total_paid': total_paid,
        'balance': balance,
        'school_settings': SchoolSettings.load(
            student.user.school
            ),
    }


@login_required
@billing_required
def student_bill(request, student_id, term_id):

    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school
    )

    term = get_object_or_404(
        Term,
        id=term_id,
        session__school=request.user.school
    )

    context = _bill_context_for_student(
        student,
        term
    )

    return render(
        request,
        'billing/bill.html',
        context
    )


@login_required
@billing_required
def student_bill_pdf(request, student_id, term_id):

    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school
    )

    term = get_object_or_404(
        Term,
        id=term_id,
        session__school=request.user.school
    )

    context = _bill_context_for_student(
        student,
        term
    )

    template = get_template(
        'billing/bill.html'
    )

    html_string = template.render(
        context,
        request=request
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; '
        f'filename="{student.admission_number}_bill.pdf"'
    )

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)

    return response


@login_required
@billing_required
def class_bill_pdf(request, class_id, term_id):

    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=request.user.school
    )

    term = get_object_or_404(
        Term,
        id=term_id,
        session__school=request.user.school
    )

    students = Student.objects.filter(
        school_class=school_class,
        user__school=request.user.school,
        is_active=True
    )

    bills = [
        _bill_context_for_student(
            student,
            term
        )
        for student in students
    ]

    template = get_template(
        'billing/class_bills.html'
    )

    html_string = template.render(
        {
            'bills': bills,
            'school_class': school_class,
            'term': term,
        },
        request=request
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; '
        f'filename="{school_class}_bills.pdf"'
    )

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf(response)

    return response


@login_required
@billing_required
def edit_opening_balance(request, balance_id):

    balance_queryset = OpeningBalance.objects.all()

    if not request.user.is_superuser:
        balance_queryset = balance_queryset.filter(
            student__user__school=request.user.school
        )

    balance = get_object_or_404(
        balance_queryset,
        id=balance_id
    )

    if request.method == "POST":

        form = OpeningBalanceForm(
            request.POST,
            instance=balance,
            user=request.user
        )

        if form.is_valid():

            updated_balance = form.save(commit=False)

            if (
                not request.user.is_superuser
                and updated_balance.student.user.school_id
                != request.user.school_id
            ):
                raise PermissionDenied(
                    "You cannot assign an opening balance "
                    "to a student from another school."
                )

            updated_balance.save()

            return redirect(
                "opening_balance_list"
            )

    else:

        form = OpeningBalanceForm(
            instance=balance,
            user=request.user
        )

    return render(
        request,
        "billing/add_opening_balance.html",
        {
            "form": form,
            "fee_structure_list_url": "/billing/opening-balances/",
        },
    )
    
@login_required
@billing_required
def delete_opening_balance(request, balance_id):

    balance_queryset = OpeningBalance.objects.all()

    if not request.user.is_superuser:
        balance_queryset = balance_queryset.filter(
            student__user__school=request.user.school
        )

    balance = get_object_or_404(
        balance_queryset,
        id=balance_id
    )

    balance.delete()

    return redirect(
        "opening_balance_list"
    )


@login_required
@billing_required
def payment_list(request):

    payments = Payment.objects.select_related(
        "student",
        "student__user",
        "student__school_class",
        "term",
    ).filter(
        student__user__school=request.user.school
    ).order_by(
        "-date_paid",
        "-id"
    )

    search = request.GET.get("search")
    class_id = request.GET.get("class")
    term_id = request.GET.get("term")
    method = request.GET.get("method")

    if search:
        payments = payments.filter(
            Q(receipt_number__icontains=search)
            | Q(student__admission_number__icontains=search)
            | Q(student__user__first_name__icontains=search)
            | Q(student__user__last_name__icontains=search)
        )

    if class_id:
        payments = payments.filter(
            student__school_class_id=class_id,
            student__school_class__school=request.user.school
        )

    if term_id:
        payments = payments.filter(
            term_id=term_id,
            term__session__school=request.user.school
        )

    if method:
        payments = payments.filter(
            payment_method=method
        )

    return render(
        request,
        "billing/payment_list.html",
        {
            "payments": payments,
            "classes": SchoolClass.objects.filter(
                school=request.user.school
            ),
            "terms": Term.objects.filter(
                session__school=request.user.school
            ),
            "methods": Payment.PAYMENT_METHODS,
            "selected_class": class_id or "",
            "selected_term": term_id or "",
            "selected_method": method or "",
        },
    )
    
@login_required
@billing_required
def payment_receipt(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id,
        student__user__school=request.user.school
    )

    context = {
        "payment": payment,
        "school_settings": SchoolSettings.load(
            payment.student.user.school
            ),
    }

    return render(
        request,
        "billing/payment_receipt.html",
        context
    )
    

@login_required
@billing_required
def payment_receipt_pdf(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id,
        student__user__school=request.user.school
    )

    context = {
        "payment": payment,
        "school_settings": SchoolSettings.load(
            payment.student.user.school
        ),
    }

    template = get_template(
        "billing/payment_receipt.html"
    )

    html_string = template.render(
        context,
        request=request
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
    )

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf(response)

    return response

@login_required
@billing_required
def student_payment_history(request, student_id):

    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school
    )

    payments = Payment.objects.filter(
        student=student,
        student__user__school=request.user.school
    ).select_related(
        "term",
        "recorded_by"
    ).order_by(
        "-date_paid"
    )

    total_paid = payments.aggregate(
        total=models.Sum("amount")
    )["total"] or 0

    return render(
        request,
        "billing/student_payment_history.html",
        {
            "student": student,
            "payments": payments,
            "total_paid": total_paid,
        }
    )
    
