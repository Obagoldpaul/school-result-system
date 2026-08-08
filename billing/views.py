from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML
from accounts.decorators import management_required
from students.models import Student, SchoolClass
from academics.models import Term, SchoolSettings
from .forms import FeeStructureForm, PaymentForm, OpeningBalanceForm
from .models import FeeStructure, Payment, OpeningBalance, get_cumulative_balance
from django.db.models import Sum
from django.db.models import Q
from django.db import models
from django.contrib import messages
from accounts.decorators import billing_required



@billing_required
@login_required
def billing_dashboard(request):

    current_term = Term.objects.filter(
        is_current=True
    ).first()

    total_students = Student.objects.filter(
        is_active=True
    ).count()

    total_fee_structures = FeeStructure.objects.count()

    total_opening_balances = OpeningBalance.objects.count()

    total_payments = Payment.objects.count()
    
    recent_payments = Payment.objects.select_related(
        "student",
        "student__user",
        "term",
        "recorded_by"
    ).order_by(
    "-date_paid"
    )[:5]

    total_collected = Payment.objects.aggregate(
        total=Sum("amount")
    )["total"] or 0

    expected_revenue = 0
    collection_rate = 0
    students_owing = 0
    outstanding = 0

    if current_term:

        students = Student.objects.filter(
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

@billing_required
@login_required
def add_fee_structure(request):
    if request.method == 'POST':
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('fee_structure_list')
    else:
        form = FeeStructureForm()
    return render(request, 'billing/add_fee_structure.html', {
    'form': form,
    'fee_structure_list_url': '/billing/fees/',
    'page_title': 'Add Fee Structure',
    })

@billing_required
@login_required
def edit_fee_structure(request, fee_id):

    fee = get_object_or_404(
        FeeStructure,
        id=fee_id
    )

    if request.method == "POST":

        form = FeeStructureForm(
            request.POST,
            instance=fee
        )

        if form.is_valid():

            form.save()

            return redirect(
                "fee_structure_list"
            )

    else:

        form = FeeStructureForm(
            instance=fee
        )

    return render(request, 'billing/add_fee_structure.html', {
    'form': form,
    'fee_structure_list_url': '/billing/fees/',
    'page_title': 'Edit Fee Structure',
    })
    
@billing_required
@login_required
def delete_fee_structure(request, fee_id):

    fee = get_object_or_404(
        FeeStructure,
        id=fee_id
    )

    # Prevent accidental deletion
    if request.method == "POST":

        success_message = (f"Fee structure for {fee.school_class} ({fee.term}) was deleted successfully.")

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

@billing_required
@login_required
def fee_structure_list(request):

    fees = FeeStructure.objects.select_related(
        "school_class",
        "department",
        "term"
    )

    search = request.GET.get("search", "")

    if search:
        fees = fees.filter(
            school_class__name__icontains=search
        )

    context = {

        "fees": fees,

        "search": search,

        "total_fees": FeeStructure.objects.count(),

        "total_classes":
            FeeStructure.objects.values(
                "school_class"
            ).distinct().count(),

        "total_terms":
            FeeStructure.objects.values(
                "term"
            ).distinct().count(),

    }

    return render(
        request,
        "billing/fee_structure_list.html",
        context,
    )
    

@billing_required
@login_required
def fee_structure_students(request, fee_id):

    fee = get_object_or_404(
        FeeStructure,
        id=fee_id
    )

    students = Student.objects.select_related(
        "user",
        "school_class",
        "department"
    ).filter(
        school_class=fee.school_class,
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

@billing_required
@login_required
def record_payment(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)

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


@billing_required
@login_required
def students_owing(request):
    class_id = request.GET.get('class')
    term_id = request.GET.get('term') or (Term.objects.filter(is_current=True).first() and Term.objects.filter(is_current=True).first().id)

    students = Student.objects.filter(is_active=True)
    if class_id:
        students = students.filter(school_class_id=class_id)

    rows = []
    term = None
    if term_id:
        term = get_object_or_404(Term, id=term_id)
        for student in students:
            fee_amount, total_paid, balance = get_cumulative_balance(student, term)
            if balance is not None and balance > 0:
                rows.append({
                    'student': student,
                    'fee_amount': fee_amount,
                    'total_paid': total_paid,
                    'balance': balance,
                })

    return render(request, 'billing/students_owing.html', {
        'rows': rows,
        'classes': SchoolClass.objects.all(),
        'terms': Term.objects.all(),
        'selected_class': class_id,
        'selected_term': term_id,
        'term': term,
    })


@billing_required
@login_required
def add_opening_balance(request):
    if request.method == 'POST':
        form = OpeningBalanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('students_owing')
    else:
        form = OpeningBalanceForm()
    return render(request, 'billing/add_opening_balance.html', {
        'form': form,
        'students_owing_url': '/billing/owing/',
    })


@billing_required
@login_required
def opening_balance_list(request):

    balances = OpeningBalance.objects.select_related(
        "student",
        "student__user"
    )

    search = request.GET.get("search", "")

    if search:

        balances = balances.filter(
            student__user__first_name__icontains=search
        ) | balances.filter(
            student__user__last_name__icontains=search
        ) | balances.filter(
            student__admission_number__icontains=search
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
        'school_settings': SchoolSettings.load(),
    }


@billing_required
@login_required
def student_bill(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    context = _bill_context_for_student(student, term)
    return render(request, 'billing/bill.html', context)


@billing_required
@login_required
def student_bill_pdf(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    context = _bill_context_for_student(student, term)

    template = get_template('billing/bill.html')
    html_string = template.render(context, request=request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.admission_number}_bill.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(response)
    return response


@billing_required
@login_required
def class_bill_pdf(request, class_id, term_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    term = get_object_or_404(Term, id=term_id)
    students = Student.objects.filter(school_class=school_class, is_active=True)

    bills = [_bill_context_for_student(s, term) for s in students]

    template = get_template('billing/class_bills.html')
    html_string = template.render({'bills': bills, 'school_class': school_class, 'term': term}, request=request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{school_class}_bills.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(response)
    return response


@billing_required
@login_required
def edit_opening_balance(request, balance_id):

    balance = get_object_or_404(
        OpeningBalance,
        id=balance_id
    )

    if request.method == "POST":

        form = OpeningBalanceForm(
            request.POST,
            instance=balance
        )

        if form.is_valid():

            form.save()

            return redirect(
                "opening_balance_list"
            )

    else:

        form = OpeningBalanceForm(
            instance=balance
        )

    return render(
        request,
        "billing/add_opening_balance.html",
        {
            "form": form,
            "fee_structure_list_url": "/billing/opening-balances/",
        },
    )
    
@billing_required
@login_required
def delete_opening_balance(request, balance_id):

    balance = get_object_or_404(
        OpeningBalance,
        id=balance_id
    )

    balance.delete()

    return redirect(
        "opening_balance_list"
    )


@billing_required
@login_required
def payment_list(request):

    payments = Payment.objects.select_related(
        "student",
        "student__user",
        "student__school_class",
        "term",
    ).order_by("-date_paid", "-id")

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
            student__school_class_id=class_id
        )

    if term_id:
        payments = payments.filter(
            term_id=term_id
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
            "classes": SchoolClass.objects.all(),
            "terms": Term.objects.all(),
            "methods": Payment.PAYMENT_METHODS,
            "search": search or "",
            "selected_class": class_id or "",
            "selected_term": term_id or "",
            "selected_method": method or "",
        },
    )
    
@billing_required
@login_required
def payment_receipt(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    context = {
        "payment": payment,
        "school_settings": SchoolSettings.load(),
    }

    return render(
        request,
        "billing/payment_receipt.html",
        context
    )
    

@billing_required
@login_required
def payment_receipt_pdf(request, payment_id):

    payment = get_object_or_404(
        Payment,
        id=payment_id
    )

    context = {
        "payment": payment,
        "school_settings": SchoolSettings.load(),
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

@billing_required
@login_required
def student_payment_history(request, student_id):

    student = get_object_or_404(
        Student,
        id=student_id
    )

    payments = Payment.objects.filter(
        student=student
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
    
@billing_required
@login_required
def student_payment_history(request, student_id):

    student = get_object_or_404(
        Student,
        id=student_id
    )

    payments = Payment.objects.filter(
        student=student
    ).order_by('-date_paid')

    return render(
        request,
        "billing/student_payment_history.html",
        {
            "student": student,
            "payments": payments,
        }
    )
    
