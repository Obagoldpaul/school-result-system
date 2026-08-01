from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.decorators import management_required
from students.models import Student, SchoolClass
from academics.models import Term
from .forms import FeeStructureForm, PaymentForm
from .models import FeeStructure, Payment, get_cumulative_balance


@management_required
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
    })


@management_required
@login_required
def fee_structure_list(request):
    fees = FeeStructure.objects.select_related('school_class', 'department', 'term')
    return render(request, 'billing/fee_structure_list.html', {'fees': fees})


@management_required
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
            return redirect('students_owing')
    else:
        form = PaymentForm()

    from .models import FeeStructure, Payment, get_cumulative_balance

    fee_amount, total_paid, balance = get_cumulative_balance(student, term)

    return render(request, 'billing/record_payment.html', {
        'form': form,
        'student': student,
        'term': term,
        'fee_amount': fee_amount,
        'total_paid': total_paid,
        'balance': balance,
    })


@management_required
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

    from .models import OpeningBalance
from .forms import OpeningBalanceForm

@management_required
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