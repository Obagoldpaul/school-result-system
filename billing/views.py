from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.http import HttpResponse, JsonResponse
from weasyprint import HTML
from accounts.decorators import management_required
from accounts.permissions import (
    can_manage_billing,
    is_student,
)
from accounts.utils import get_current_term
from students.models import Student, SchoolClass
from academics.models import (
    AcademicSession,
    Term,
    SchoolSettings,
)
from .forms import (
    FeeCategoryForm,
    FeeAssignmentForm,
    PaymentForm,
    OpeningBalanceForm,
    PaymentAllocationFormSet,
    StudentBillForm,
    OpeningBalancePaymentForm,
)
from .models import (
    FeeCategory,
    FeeAssignment,
    Payment,
    OpeningBalance,
    OpeningBalancePayment,
    PaymentAllocation,
    OptionalFeeEnrollment,
    get_fee_assignments_for_student,
    get_student_fee_breakdown,
    get_student_account_summary,
)
from django.db.models import Sum, Count
from django.db.models import Q
from django.db import models
from django.contrib import messages
from accounts.decorators import billing_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django import forms
from decimal import Decimal
from academics.utils import get_term_order



@login_required
@billing_required
def billing_dashboard(request):

    school = request.user.school
    current_term = get_current_term(request.user)

    total_students = Student.objects.filter(
        school_class__school=school,
        is_active=True
    ).count()

    total_fee_assignments = FeeAssignment.objects.filter(
        fee_category__school=school,
        is_active=True,
    ).count()
    
    total_fee_categories = FeeCategory.objects.filter(
        school=school,
        is_active=True,
    ).count()

    compulsory_assignments = FeeAssignment.objects.filter(
        fee_category__school=school,
        fee_category__category_type="COMPULSORY",
        is_active=True,
    ).count()

    optional_assignments = FeeAssignment.objects.filter(
        fee_category__school=school,
        fee_category__category_type="OPTIONAL",
        is_active=True,
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

    current_term_collected = 0
    expected_revenue = 0
    collection_rate = 0
    students_owing = 0
    outstanding = 0

    if current_term:

        students = Student.objects.filter(
            user__school=school,
            is_active=True
        )

        # ---------------------------------------------------------
        # CURRENT TERM PAYMENTS
        # ---------------------------------------------------------

        current_term_collected = Payment.objects.filter(
            student__user__school=school,
            term=current_term,
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        # ---------------------------------------------------------
        # CURRENT TERM EXPECTED REVENUE
        #
        # Uses the NEW FeeAssignment system.
        #
        # Compulsory fees are automatically included.
        # Optional fees are included only for students
        # who have opted in.
        # ---------------------------------------------------------

        for student in students:

            assignments = get_fee_assignments_for_student(
                student,
                current_term
            )

            student_expected = sum(
                assignment.amount
                for assignment in assignments
            )

            expected_revenue += student_expected

        # ---------------------------------------------------------
        # CURRENT TERM OUTSTANDING
        # ---------------------------------------------------------

        outstanding = max(
            expected_revenue - current_term_collected,
            0
        )

        # ---------------------------------------------------------
        # STUDENTS OWING
        #
        # A student is owing if their applicable current-term
        # fees are greater than the payments recorded for them
        # for the current term.
        # ---------------------------------------------------------

        for student in students:

            assignments = get_fee_assignments_for_student(
                student,
                current_term
            )

            student_expected = sum(
                assignment.amount
                for assignment in assignments
            )

            student_paid = Payment.objects.filter(
                student=student,
                term=current_term,
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            if student_expected > student_paid:

                students_owing += 1

        # ---------------------------------------------------------
        # COLLECTION RATE
        # ---------------------------------------------------------

        if expected_revenue > 0:

            collection_rate = (
                current_term_collected / expected_revenue
            ) * 100

    context = {

        "current_term": current_term,

        "total_students": total_students,

        "total_fee_assignments": total_fee_assignments,
        
        "total_fee_categories": total_fee_categories,

        "compulsory_assignments": compulsory_assignments,

        "optional_assignments": optional_assignments,

        "total_opening_balances": total_opening_balances,

        "total_payments": total_payments,

        "total_collected": total_collected,
        
        "current_term_collected": current_term_collected,

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
def fee_category_list(request):

    categories = FeeCategory.objects.annotate(
        assignment_count=Count(
            "assignments"
        )
    ).order_by(
        "name"
    )

    if not request.user.is_superuser:

        categories = categories.filter(
            school_id=request.user.school_id
        )

    return render(
        request,
        "billing/fee_category_list.html",
        {
            "categories": categories,
        },
    )


@login_required
@billing_required
def add_fee_category(request):

    if request.method == "POST":

        form = FeeCategoryForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Fee category created successfully."
            )

            return redirect(
                "fee_category_list"
            )

    else:

        form = FeeCategoryForm(
            user=request.user,
        )

    return render(
        request,
        "billing/add_fee_category.html",
        {
            "form": form,
            "page_title": "Add Fee Category",
        },
    )


@login_required
@billing_required
def edit_fee_category(request, category_id):

    category_queryset = FeeCategory.objects.all()

    if not request.user.is_superuser:

        category_queryset = category_queryset.filter(
            school_id=request.user.school_id
        )

    category = get_object_or_404(
        category_queryset,
        id=category_id,
    )

    if request.method == "POST":

        form = FeeCategoryForm(
            request.POST,
            instance=category,
            user=request.user,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Fee category updated successfully."
            )

            return redirect(
                "fee_category_list"
            )

    else:

        form = FeeCategoryForm(
            instance=category,
            user=request.user,
        )

    return render(
        request,
        "billing/edit_fee_category.html",
        {
            "form": form,
            "category": category,
            "page_title": "Edit Fee Category",
        },
    )


@login_required
@billing_required
def toggle_fee_category(request, category_id):

    category_queryset = FeeCategory.objects.all()

    if not request.user.is_superuser:

        category_queryset = category_queryset.filter(
            school=request.user.school
        )

    category = get_object_or_404(
        category_queryset,
        id=category_id,
    )

    category.is_active = not category.is_active

    category.save(
        update_fields=["is_active"]
    )

    if category.is_active:

        messages.success(
            request,
            f"{category.name} has been activated."
        )

    else:

        messages.success(
            request,
            f"{category.name} has been deactivated."
        )

    return redirect(
        "fee_category_list"
    )

@login_required
@billing_required
def add_fee_assignment(request):

    if request.method == "POST":

        form = FeeAssignmentForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            assignment = form.save(
                commit=False
            )

            # -------------------------------------------------
            # SECURITY CHECKS
            # -------------------------------------------------

            if not request.user.is_superuser:

                if (
                    assignment.fee_category.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a fee category "
                        "from another school."
                    )

                if (
                    assignment.term.session.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a term "
                        "from another school."
                    )

                if (
                    assignment.school_class
                    and assignment.school_class.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot assign a fee "
                        "to another school."
                    )

                if (
                    assignment.department
                    and assignment.department.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a department "
                        "from another school."
                    )

                if (
                    assignment.student
                    and assignment.student.user.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot assign a fee "
                        "to a student from another school."
                    )

            assignment.save()

            messages.success(
                request,
                "Fee assignment created successfully."
            )

            return redirect(
                "fee_assignment_list"
            )

    else:

        form = FeeAssignmentForm(
            user=request.user,
        )

    return render(
        request,
        "billing/add_fee_assignment.html",
        {
            "form": form,
            "page_title": "Add Fee Assignment",
        },
    )
    
@login_required
@billing_required
def fee_assignment_student_search(request):
    """
    Search active students for Fee Assignment.

    Results are restricted to the logged-in user's school.
    A class can optionally be supplied to narrow the search.
    """

    query = request.GET.get("q", "").strip()
    class_id = request.GET.get("class_id", "").strip()

    # ---------------------------------------------------------
    # SCHOOL-SCOPED STUDENTS
    # ---------------------------------------------------------

    if request.user.is_superuser:

        students = Student.objects.filter(
            is_active=True
        ).select_related(
            "user",
            "school_class",
        )

    else:

        students = Student.objects.filter(
            user__school=request.user.school,
            is_active=True,
        ).select_related(
            "user",
            "school_class",
        )

    # ---------------------------------------------------------
    # FILTER BY CLASS
    # ---------------------------------------------------------

    if class_id:

        students = students.filter(
            school_class_id=class_id
        )

    # ---------------------------------------------------------
    # SEARCH BY NAME OR ADMISSION NUMBER
    # ---------------------------------------------------------

    if query:

        students = students.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(admission_number__icontains=query)
        )

    # ---------------------------------------------------------
    # LIMIT RESULTS
    #
    # Never send hundreds of students to the browser.
    # ---------------------------------------------------------

    students = students[:20]

    results = []

    for student in students:

        full_name = (
            student.user.get_full_name()
            or student.user.username
        )

        results.append({
            "id": student.id,
            "name": full_name,
            "admission_number": student.admission_number,
            "class_name": (
                str(student.school_class)
                if student.school_class
                else ""
            ),
        })

    return JsonResponse({
        "students": results,
    })

@login_required
@billing_required
def manage_optional_fee_students(request, assignment_id):
    """
    Manage students enrolled in an optional fee assignment.

    Allows staff to:
    - View students applicable to the assignment
    - Opt students in
    - Remove students from the optional fee
    - Search students by name or admission number
    """

    # ---------------------------------------------------------
    # GET ASSIGNMENT
    # ---------------------------------------------------------

    assignment_queryset = FeeAssignment.objects.select_related(
        "fee_category",
        "term",
        "school_class",
        "department",
    )

    if not request.user.is_superuser:
        assignment_queryset = assignment_queryset.filter(
            fee_category__school=request.user.school
        )

    assignment = get_object_or_404(
        assignment_queryset,
        id=assignment_id,
    )

    # ---------------------------------------------------------
    # OPTIONAL FEE ONLY
    # ---------------------------------------------------------

    if assignment.fee_category.category_type != "OPTIONAL":
        messages.error(
            request,
            "Student enrollment management is only available "
            "for optional fees."
        )

        return redirect("fee_assignment_list")

    # ---------------------------------------------------------
    # DETERMINE APPLICABLE STUDENTS
    # ---------------------------------------------------------

    students_queryset = Student.objects.filter(
        is_active=True,
    )

    if assignment.student_id:

        # Individual student assignment
        students_queryset = students_queryset.filter(
            id=assignment.student_id
        )

    elif assignment.department_id:

        # Class + department assignment
        students_queryset = students_queryset.filter(
            school_class_id=assignment.school_class_id,
            department_id=assignment.department_id,
        )

    elif assignment.school_class_id:

        # Class-wide assignment
        students_queryset = students_queryset.filter(
            school_class_id=assignment.school_class_id,
        )

    else:

        students_queryset = Student.objects.none()

    # ---------------------------------------------------------
    # SCHOOL SECURITY
    # ---------------------------------------------------------

    if not request.user.is_superuser:

        students_queryset = students_queryset.filter(
            user__school=request.user.school
        )

    students_queryset = students_queryset.select_related(
        "user",
        "school_class",
        "department",
    )

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        from django.db.models import Q

        students_queryset = students_queryset.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__other_name__icontains=search)
            | Q(admission_number__icontains=search)
        )

    # ---------------------------------------------------------
    # GET EXISTING ENROLLMENTS
    # ---------------------------------------------------------

    enrollments = OptionalFeeEnrollment.objects.filter(
        fee_assignment=assignment,
        student__in=students_queryset,
    )

    enrollment_map = {
        enrollment.student_id: enrollment
        for enrollment in enrollments
    }

    # ---------------------------------------------------------
    # BUILD STUDENT LIST
    # ---------------------------------------------------------

    student_records = []

    for student in students_queryset:

        enrollment = enrollment_map.get(
            student.id
        )

        student_records.append(
            {
                "student": student,
                "enrollment": enrollment,
                "opted_in": (
                    enrollment.opted_in
                    if enrollment
                    else False
                ),
            }
        )

    # ---------------------------------------------------------
    # HANDLE ACTION
    # ---------------------------------------------------------

    if request.method == "POST":

        student_id = request.POST.get(
            "student_id"
        )

        action = request.POST.get(
            "action"
        )

        student = get_object_or_404(
            students_queryset,
            id=student_id,
        )

        enrollment, created = (
            OptionalFeeEnrollment.objects.get_or_create(
                fee_assignment=assignment,
                student=student,
                defaults={
                    "opted_in": True,
                },
            )
        )

        if action == "opt_in":

            enrollment.opted_in = True

            enrollment.save(
                update_fields=[
                    "opted_in",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"{student} has been added to "
                f"{assignment.fee_category.name}."
            )

        elif action == "opt_out":

            enrollment.opted_in = False

            enrollment.save(
                update_fields=[
                    "opted_in",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                f"{student} has been removed from "
                f"{assignment.fee_category.name}."
            )

        return redirect(
            "manage_optional_fee_students",
            assignment_id=assignment.id,
        )

    return render(
        request,
        "billing/manage_optional_fee_students.html",
        {
            "assignment": assignment,
            "student_records": student_records,
            "search": search,
            "total_students": students_queryset.count(),
        },
    )

@login_required
@billing_required
def fee_assignment_list(request):
    """
    Display fee assignments with filtering and search.

    Filters:
    - Academic session
    - Term
    - Fee category
    - Compulsory / Optional
    - Active / Inactive
    - Search by student, admission number, class, or fee category
    """

    # ---------------------------------------------------------
    # BASE QUERYSET
    # ---------------------------------------------------------

    assignments = FeeAssignment.objects.select_related(
        "fee_category",
        "term",
        "term__session",
        "school_class",
        "department",
        "student",
        "student__user",
    ).annotate(
        enrollment_count=Count(
            "optional_enrollments",
            filter=Q(
                optional_enrollments__opted_in=True
            ),
        )
    )

    # ---------------------------------------------------------
    # SCHOOL SECURITY
    # ---------------------------------------------------------

    if not request.user.is_superuser:
        assignments = assignments.filter(
            fee_category__school=request.user.school
        )

    # ---------------------------------------------------------
    # FILTER VALUES
    # ---------------------------------------------------------

    session_id = request.GET.get("session")
    term_id = request.GET.get("term")
    category_id = request.GET.get("category")
    category_type = request.GET.get("type")
    status = request.GET.get("status")
    search = request.GET.get("search", "").strip()

    # ---------------------------------------------------------
    # SESSION FILTER
    # ---------------------------------------------------------

    if session_id:
        assignments = assignments.filter(
            term__session_id=session_id
        )

    # ---------------------------------------------------------
    # TERM FILTER
    # ---------------------------------------------------------

    if term_id:
        assignments = assignments.filter(
            term_id=term_id
        )

    # ---------------------------------------------------------
    # FEE CATEGORY FILTER
    # ---------------------------------------------------------

    if category_id:
        assignments = assignments.filter(
            fee_category_id=category_id
        )

    # ---------------------------------------------------------
    # CATEGORY TYPE FILTER
    # ---------------------------------------------------------

    if category_type in ["COMPULSORY", "OPTIONAL"]:
        assignments = assignments.filter(
            fee_category__category_type=category_type
        )

    # ---------------------------------------------------------
    # STATUS FILTER
    # ---------------------------------------------------------

    if status == "active":
        assignments = assignments.filter(
            is_active=True
        )

    elif status == "inactive":
        assignments = assignments.filter(
            is_active=False
        )

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    if search:

        assignments = assignments.filter(
            Q(fee_category__name__icontains=search)
            | Q(student__user__first_name__icontains=search)
            | Q(student__user__last_name__icontains=search)
            | Q(student__user__other_name__icontains=search)
            | Q(student__admission_number__icontains=search)
            | Q(school_class__name__icontains=search)
        )

    # ---------------------------------------------------------
    # ORDERING
    # ---------------------------------------------------------

    assignments = assignments.order_by(
        "term__session__name",
        "term",
        "fee_category__name",
    )

    # ---------------------------------------------------------
    # FILTER DROPDOWNS
    # ---------------------------------------------------------

    sessions = AcademicSession.objects.all().order_by(
        "-name"
    )

    terms = Term.objects.select_related(
        "session"
    ).all()

    categories = FeeCategory.objects.filter(
        is_active=True
    ).order_by(
        "name"
    )

    # ---------------------------------------------------------
    # SCHOOL SECURITY FOR FILTER DROPDOWNS
    # ---------------------------------------------------------

    if not request.user.is_superuser:

        sessions = sessions.filter(
            school=request.user.school
        )

        terms = terms.filter(
            session__school=request.user.school
        )

        categories = categories.filter(
            school=request.user.school
        )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "assignments": assignments,
        "sessions": sessions,
        "terms": terms,
        "categories": categories,

        "selected_session": session_id,
        "selected_term": term_id,
        "selected_category": category_id,
        "selected_type": category_type,
        "selected_status": status,
        "search": search,
    }

    return render(
        request,
        "billing/fee_assignment_list.html",
        context,
    )

@login_required
@billing_required
def fee_assignment_terms(request):

    session_id = request.GET.get("session")

    if not session_id:
        return JsonResponse(
            {"terms": []}
        )

    terms_queryset = Term.objects.filter(
        session_id=session_id
    )

    if not request.user.is_superuser:

        terms_queryset = terms_queryset.filter(
            session__school=request.user.school
        )

    terms = [
        {
            "id": term.id,
            "name": term.get_name_display(),
        }
        for term in terms_queryset
    ]

    return JsonResponse(
        {"terms": terms}
    )

@login_required
@billing_required
def edit_fee_assignment(request, assignment_id):

    assignment_queryset = FeeAssignment.objects.select_related(
        "fee_category",
        "term",
        "school_class",
        "department",
        "student",
    )

    if not request.user.is_superuser:
        assignment_queryset = assignment_queryset.filter(
            fee_category__school=request.user.school
        )

    assignment = get_object_or_404(
        assignment_queryset,
        id=assignment_id,
    )

    if request.method == "POST":

        form = FeeAssignmentForm(
            request.POST,
            instance=assignment,
            user=request.user,
        )

        if form.is_valid():

            updated_assignment = form.save(
                commit=False
            )

            # -------------------------------------------------
            # SECURITY CHECKS
            # -------------------------------------------------

            if not request.user.is_superuser:

                if (
                    updated_assignment.fee_category.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a fee category "
                        "from another school."
                    )

                if (
                    updated_assignment.term.session.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a term "
                        "from another school."
                    )

                if (
                    updated_assignment.school_class
                    and updated_assignment.school_class.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot assign a fee "
                        "to another school."
                    )

                if (
                    updated_assignment.department
                    and updated_assignment.department.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot use a department "
                        "from another school."
                    )

                if (
                    updated_assignment.student
                    and updated_assignment.student.user.school_id
                    != request.user.school_id
                ):
                    raise PermissionDenied(
                        "You cannot assign a fee "
                        "to a student from another school."
                    )

            updated_assignment.save()

            messages.success(
                request,
                "Fee assignment updated successfully."
            )

            return redirect(
                "fee_assignment_list"
            )

    else:

        form = FeeAssignmentForm(
            instance=assignment,
            user=request.user,
        )

    return render(
        request,
        "billing/edit_fee_assignment.html",
        {
            "form": form,
            "assignment": assignment,
            "page_title": "Edit Fee Assignment",
        },
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

    # ---------------------------------------------------------
    # CURRENT FEE BREAKDOWN
    # ---------------------------------------------------------

    fee_breakdown = get_student_fee_breakdown(
        student,
        term
    )

    fee_category_ids = [
        item["fee_category"].id
        for item in fee_breakdown
        if item["balance"] > 0
    ]

    fee_categories = FeeCategory.objects.filter(
        id__in=fee_category_ids,
        school=student.user.school,
    ).order_by("name")

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------

    if request.method == "POST":

        form = PaymentForm(
            request.POST
        )

        allocation_formset = PaymentAllocationFormSet(
            request.POST,
            form_kwargs={
                "fee_categories": fee_categories,
                "fee_breakdown": fee_breakdown,
            }
        )

        if form.is_valid() and allocation_formset.is_valid():

            payment_amount = form.cleaned_data["amount"]

            allocation_total = 0

            allocation_data = []

            for allocation_form in allocation_formset:

                if not allocation_form.cleaned_data:
                    continue

                if allocation_form.cleaned_data.get("DELETE"):
                    continue

                category = allocation_form.cleaned_data.get(
                    "fee_category"
                )

                amount = allocation_form.cleaned_data.get(
                    "amount"
                )

                if not category or not amount:
                    continue

                allocation_total += amount

                allocation_data.append({
                    "fee_category": category,
                    "amount": amount,
                    "note": allocation_form.cleaned_data.get(
                        "note",
                        ""
                    ),
                })

            if allocation_total != payment_amount:

                allocation_formset._non_form_errors.append(
                    forms.ValidationError(
                        "The allocation total must equal "
                        "the payment amount."
                    )
                )

            else:

                valid_allocations = True
                allocated_by_category = {}

                for allocation in allocation_data:
                    category_id = allocation["fee_category"].id
                    allocated_by_category[category_id] = (
                        allocated_by_category.get(category_id, 0)
                        + allocation["amount"]
                    )

                for category_id, amount in allocated_by_category.items():

                    category = next(
                        allocation["fee_category"]
                        for allocation in allocation_data
                        if allocation["fee_category"].id == category_id
                    )

                    category_balance = 0

                    for item in fee_breakdown:

                        if (
                            item["fee_category"].id
                            == category.id
                        ):

                            category_balance = item["balance"]
                            break

                    if amount > category_balance:

                        valid_allocations = False

                        allocation_formset._non_form_errors.append(
                            forms.ValidationError(
                                f"{category.name} has only "
                                f"₦{category_balance:,.2f} "
                                f"outstanding."
                            )
                        )

                if valid_allocations:

                    with transaction.atomic():

                        payment = form.save(
                            commit=False
                        )

                        payment.student = student
                        payment.term = term
                        payment.recorded_by = request.user

                        payment.save()

                        for allocation in allocation_data:

                            PaymentAllocation.objects.create(
                                payment=payment,
                                fee_category=allocation[
                                    "fee_category"
                                ],
                                amount=allocation[
                                    "amount"
                                ],
                                note=allocation[
                                    "note"
                                ],
                            )

                    return render(
                        request,
                        "billing/payment_success.html",
                        {
                            "payment": payment,
                        }
                    )

    else:

        form = PaymentForm()

        allocation_formset = PaymentAllocationFormSet(
            initial=[
                {"fee_category": item["fee_category"].id}
                for item in fee_breakdown
                if item["balance"] > 0
            ],
            form_kwargs={
                "fee_categories": fee_categories,
                "fee_breakdown": fee_breakdown,
            }
        )

    # ---------------------------------------------------------
    # CURRENT TOTALS
    # ---------------------------------------------------------

    fee_amount = sum(
        item["amount"]
        for item in fee_breakdown
    )

    total_paid = sum(
        item["paid"]
        for item in fee_breakdown
    )

    balance = sum(
        item["balance"]
        for item in fee_breakdown
    )
    
    fee_balances = {
        str(item["fee_category"].id): str(item["balance"])
        for item in fee_breakdown
    }

    return render(
        request,
        "billing/record_payment.html",
        {
            "form": form,
            "allocation_formset": allocation_formset,
            "student": student,
            "term": term,
            "fee_amount": fee_amount,
            "total_paid": total_paid,
            "balance": balance,
            "fee_breakdown": fee_breakdown,
            "fee_balances": fee_balances,
        }
    )


@login_required
@billing_required
def students_owing(request):

    class_id = request.GET.get("class")
    session_id = request.GET.get("session")
    term_id = request.GET.get("term")

    school = request.user.school

    current_term = get_current_term(request.user)

    # ---------------------------------------------------------
    # DEFAULT SESSION / TERM
    # ---------------------------------------------------------
    # On the first visit, use the current session and term.
    # Once the user selects a session, do NOT automatically
    # force the current term if it belongs to another session.
    # ---------------------------------------------------------

    if not session_id and current_term:
        session_id = str(current_term.session_id)

    if not term_id and current_term:
        if not session_id or str(current_term.session_id) == str(session_id):
            term_id = str(current_term.id)

    # ---------------------------------------------------------
    # STUDENTS
    # ---------------------------------------------------------

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
    session = None

    # ---------------------------------------------------------
    # SELECT SESSION
    # ---------------------------------------------------------

    if session_id:

        session = get_object_or_404(
            AcademicSession,
            id=session_id,
            school=school,
        )

    # ---------------------------------------------------------
    # SELECT TERM
    # ---------------------------------------------------------

    if term_id:

        # If a session has been selected, the term MUST belong
        # to that exact session.
        if session:

            term = get_object_or_404(
                Term,
                id=term_id,
                session=session,
                session__school=school,
            )

        else:

            term = get_object_or_404(
                Term,
                id=term_id,
                session__school=school,
            )

            # Keep session synchronized with the selected term.
            session = term.session
            session_id = str(term.session_id)

    # ---------------------------------------------------------
    # ACCOUNT TERMS
    # ---------------------------------------------------------
    # Keep this unchanged so account arrears continue to show
    # outstanding balances across all sessions.
    # ---------------------------------------------------------

    account_terms = Term.objects.filter(
        session__school=school,
    ).select_related(
        "session"
    )

    # ---------------------------------------------------------
    # STUDENT OWING CALCULATION
    # ---------------------------------------------------------

    if term:

        for student in students:

            # Keep this page in sync with the allocation-based
            # student bill.
            fee_breakdown = get_student_fee_breakdown(
                student,
                term,
            )

            fee_amount = sum(
                item["amount"]
                for item in fee_breakdown
            )

            total_paid = sum(
                item["paid"]
                for item in fee_breakdown
            )

            balance = sum(
                item["balance"]
                for item in fee_breakdown
            )

            outstanding_terms = []

            term_arrears = Decimal("0.00")

            for account_term in sorted(
                account_terms,
                key=lambda item: (
                    item.session_id,
                    get_term_order(item),
                ),
            ):

                account_breakdown = get_student_fee_breakdown(
                    student,
                    account_term,
                )

                account_balance = sum(
                    (
                        item["balance"]
                        for item in account_breakdown
                    ),
                    Decimal("0.00"),
                )

                if account_balance > 0:

                    term_arrears += account_balance

                    outstanding_terms.append({
                        "term": account_term,
                        "balance": account_balance,
                    })

            account_summary = get_student_account_summary(
                student
            )

            opening_arrears = account_summary[
                "opening_arrears"
            ]

            account_arrears = account_summary[
                "account_arrears"
            ]

            if account_arrears > 0:

                rows.append({
                    "student": student,
                    "fee_amount": fee_amount,
                    "total_paid": total_paid,
                    "balance": balance,
                    "account_arrears": account_arrears,
                    "outstanding_terms": outstanding_terms,
                    "opening_arrears": opening_arrears,
                })

    # ---------------------------------------------------------
    # FILTER DATA
    # ---------------------------------------------------------

    sessions = AcademicSession.objects.filter(
        school=school
    ).order_by(
        "-name"
    )

    terms = Term.objects.filter(
        session__school=school
    ).select_related(
        "session"
    ).order_by(
        "session__name",
        "name",
    )

    # Only show terms belonging to the selected session.
    if session:

        terms = terms.filter(
            session=session
        )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "billing/students_owing.html",
        {
            "rows": rows,

            "classes": SchoolClass.objects.filter(
                school=school
            ),

            "sessions": sessions,

            "terms": terms,

            "selected_class": class_id,

            "selected_session": session_id,

            "selected_term": term_id,

            "session": session,

            "term": term,
        },
    )

@login_required
@billing_required
def students_owing_print(request):

    class_id = request.GET.get("class")
    session_id = request.GET.get("session")
    term_id = request.GET.get("term")

    school = request.user.school

    # ---------------------------------------------------------
    # VALIDATE SESSION
    # ---------------------------------------------------------

    session = get_object_or_404(
        AcademicSession,
        id=session_id,
        school=school,
    )

    # ---------------------------------------------------------
    # VALIDATE TERM
    # ---------------------------------------------------------

    term = get_object_or_404(
        Term,
        id=term_id,
        session=session,
        session__school=school,
    )

    # ---------------------------------------------------------
    # STUDENTS
    # ---------------------------------------------------------

    students = Student.objects.filter(
        user__school=school,
        is_active=True,
    ).select_related(
        "user",
        "school_class",
    )

    # ---------------------------------------------------------
    # FILTER BY CLASS
    # ---------------------------------------------------------

    selected_class = None

    if class_id:

        selected_class = get_object_or_404(
            SchoolClass,
            id=class_id,
            school=school,
        )

        students = students.filter(
            school_class=selected_class,
        )

    # ---------------------------------------------------------
    # ACCOUNT TERMS
    # ---------------------------------------------------------

    account_terms = Term.objects.filter(
        session__school=school,
    ).select_related(
        "session",
    )

    # ---------------------------------------------------------
    # BUILD PRINT ROWS
    # ---------------------------------------------------------

    rows = []

    for student in students:

        fee_breakdown = get_student_fee_breakdown(
            student,
            term,
        )

        fee_amount = sum(
            item["amount"]
            for item in fee_breakdown
        )

        total_paid = sum(
            item["paid"]
            for item in fee_breakdown
        )

        balance = sum(
            item["balance"]
            for item in fee_breakdown
        )

        # -----------------------------------------------------
        # ACCOUNT ARREARS
        # -----------------------------------------------------

        outstanding_terms = []

        for account_term in sorted(
            account_terms,
            key=lambda item: (
                item.session_id,
                get_term_order(item),
            ),
        ):

            account_breakdown = get_student_fee_breakdown(
                student,
                account_term,
            )

            account_balance = sum(
                (
                    item["balance"]
                    for item in account_breakdown
                ),
                Decimal("0.00"),
            )

            if account_balance > 0:

                outstanding_terms.append({
                    "term": account_term,
                    "balance": account_balance,
                })

        account_summary = get_student_account_summary(
            student
        )

        opening_arrears = account_summary[
            "opening_arrears"
        ]

        account_arrears = account_summary[
            "account_arrears"
        ]

        # -----------------------------------------------------
        # ONLY INCLUDE STUDENTS WHO OWE
        # -----------------------------------------------------

        if account_arrears > 0:

            rows.append({
                "student": student,
                "fee_amount": fee_amount,
                "total_paid": total_paid,
                "balance": balance,
                "account_arrears": account_arrears,
                "outstanding_terms": outstanding_terms,
                "opening_arrears": opening_arrears,
            })

    # ---------------------------------------------------------
    # RENDER PRINT PAGE
    # ---------------------------------------------------------

    return render(
        request,
        "billing/students_owing_print.html",
        {
            "rows": rows,
            "school": school,
            "session": session,
            "term": term,
            "selected_class": selected_class,
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
def pay_opening_balance(request, balance_id):

    # ---------------------------------------------------------
    # GET OPENING BALANCE
    # ---------------------------------------------------------

    opening_balance_queryset = OpeningBalance.objects.select_related(
        "student",
        "student__user",
    )

    # ---------------------------------------------------------
    # SCHOOL SECURITY
    # ---------------------------------------------------------

    if not request.user.is_superuser:

        opening_balance_queryset = opening_balance_queryset.filter(
            student__user__school=request.user.school
        )

    opening_balance = get_object_or_404(
        opening_balance_queryset,
        id=balance_id,
    )

    # ---------------------------------------------------------
    # CALCULATE PAYMENT HISTORY
    # ---------------------------------------------------------

    total_paid = (
        opening_balance.payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_balance = (
        opening_balance.amount - total_paid
    )

    # ---------------------------------------------------------
    # PREVENT PAYMENT WHEN FULLY PAID
    # ---------------------------------------------------------

    if remaining_balance <= Decimal("0.00"):

        messages.info(
            request,
            "This opening balance has already been fully paid."
        )

        return redirect(
            "billing:opening_balance_list"
        )

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------

    if request.method == "POST":

        form = OpeningBalancePaymentForm(
            request.POST,
            opening_balance=opening_balance,
        )

        if form.is_valid():

            with transaction.atomic():

                payment = form.save(
                    commit=False
                )

                payment.opening_balance = (
                    opening_balance
                )

                payment.recorded_by = (
                    request.user
                )

                payment.save()

            messages.success(
                request,
                (
                    f"Opening balance payment of "
                    f"₦{payment.amount:,.2f} recorded successfully."
                )
            )

            return render(
                request,
                "billing/opening_balance_payment_success.html",
                {
                    "payment": payment,
                    "opening_balance": opening_balance,
                },
            )

    else:

        form = OpeningBalancePaymentForm(
            opening_balance=opening_balance,
        )

    # ---------------------------------------------------------
    # REFRESH PAYMENT TOTALS
    # ---------------------------------------------------------

    total_paid = (
        opening_balance.payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_balance = (
        opening_balance.amount - total_paid
    )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "billing/pay_opening_balance.html",
        {
            "form": form,
            "opening_balance": opening_balance,
            "student": opening_balance.student,
            "total_paid": total_paid,
            "remaining_balance": remaining_balance,
        },
    )

@login_required
@billing_required
def opening_balance_list(request):

    balances = OpeningBalance.objects.select_related(
        "student",
        "student__user"
    ).filter(
        student__user__school=request.user.school
    ).annotate(
        total_paid=Sum("payments__amount")
    )

    search = request.GET.get("search", "")

    if search:

        balances = balances.filter(
            Q(student__user__first_name__icontains=search)
            | Q(student__user__last_name__icontains=search)
            | Q(student__admission_number__icontains=search)
        )

    # ---------------------------------------------------------
    # CALCULATE REMAINING BALANCE
    # ---------------------------------------------------------

    for balance in balances:

        balance.total_paid = (
            balance.total_paid
            or Decimal("0.00")
        )

        balance.remaining_balance = (
            balance.amount
            - balance.total_paid
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

    fee_breakdown = get_student_fee_breakdown(
        student,
        term
    )

    fee_amount = sum(
        item["amount"]
        for item in fee_breakdown
    )

    total_paid = sum(
        item["paid"]
        for item in fee_breakdown
    )

    balance = sum(
        item["balance"]
        for item in fee_breakdown
    )

    return {
        'student': student,
        'term': term,
        'fee_amount': fee_amount,
        'total_paid': total_paid,
        'balance': balance,
        'fee_breakdown': fee_breakdown,
        'school_settings': SchoolSettings.load(
            student.user.school
        ),
    }

@login_required
@billing_required
def select_student_bill(request):

    if request.method == "POST":

        form = StudentBillForm(
            request.POST,
            user=request.user
        )

        if form.is_valid():

            student = form.cleaned_data["student"]
            term = form.cleaned_data["term"]

            return redirect(
                "student_bill",
                student_id=student.id,
                term_id=term.id
            )

    else:

        form = StudentBillForm(
            user=request.user
        )

    return render(
        request,
        "billing/select_student_bill.html",
        {
            "form": form,
        }
    )

@login_required
@billing_required
def students_by_class(request):

    school_class_id = request.GET.get("school_class")

    if not school_class_id:
        return JsonResponse(
            {"students": []}
        )

    students_queryset = Student.objects.filter(
        school_class_id=school_class_id,
        is_active=True,
        user__school=request.user.school,
    ).select_related(
        "user"
    ).order_by(
        "user__first_name",
        "user__last_name"
    )

    students = []

    for student in students_queryset:

        students.append({
            "id": student.id,
            "name": student.user.get_full_name(),
            "admission_number": student.admission_number,
        })

    return JsonResponse({
        "students": students
    })
    
@login_required
@billing_required
def terms_by_session(request):

    session_id = request.GET.get("session")

    if not session_id:
        return JsonResponse(
            {"terms": []}
        )

    session = get_object_or_404(
        AcademicSession,
        id=session_id,
        school=request.user.school,
    )

    terms_queryset = Term.objects.filter(
        session=session
    ).order_by("name")

    terms = []

    for term in terms_queryset:

        terms.append({
            "id": term.id,
            "name": term.get_name_display(),
        })

    return JsonResponse({
        "terms": terms
    })

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
def my_payment_receipt_pdf(request, payment_id):
    """
    Student-facing payment receipt.

    A student can only access a receipt belonging to
    their own payment record.
    """

    student = get_object_or_404(
        Student,
        user=request.user,
        user__school=request.user.school,
    )

    payment = get_object_or_404(
        Payment,
        id=payment_id,
        student=student,
        student__user__school=request.user.school,
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

@login_required
@billing_required
def opening_balance_payment_history(request, balance_id):

    opening_balance = get_object_or_404(
        OpeningBalance.objects.select_related(
            "student",
            "student__user",
        ),
        id=balance_id,
        student__user__school=request.user.school,
    )

    payments = (
        opening_balance.payments
        .select_related("recorded_by")
        .order_by("-date_paid", "-id")
    )

    total_paid = (
        payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_balance = (
        opening_balance.amount
        - total_paid
    )

    return render(
        request,
        "billing/opening_balance_payment_history.html",
        {
            "opening_balance": opening_balance,
            "student": opening_balance.student,
            "payments": payments,
            "total_paid": total_paid,
            "remaining_balance": remaining_balance,
        },
    )

@login_required
@billing_required
def opening_balance_payment_receipt(
    request,
    payment_id,
):

    payment = get_object_or_404(
        OpeningBalancePayment.objects.select_related(
            "opening_balance",
            "opening_balance__student",
            "opening_balance__student__user",
            "recorded_by",
        ),
        id=payment_id,
        opening_balance__student__user__school=request.user.school,
    
    )
    total_paid = (
        payment.opening_balance.payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_balance = (
        payment.opening_balance.amount
        - total_paid
    )
    
    context = {
        "student": payment.opening_balance.student,
        "payment": payment,
        "opening_balance": payment.opening_balance,
        "remaining_balance": remaining_balance,
        "school_settings": SchoolSettings.load(
            payment.opening_balance.student.user.school
        ),
    }

    return render(
        request,
        "billing/opening_balance_payment_receipt.html",
        context,
    )

@login_required
@billing_required
def opening_balance_payment_receipt_pdf(
    request,
    payment_id,
):

    payment = get_object_or_404(
        OpeningBalancePayment.objects.select_related(
            "opening_balance",
            "opening_balance__student",
            "opening_balance__student__user",
            "recorded_by",
        ),
        id=payment_id,
        opening_balance__student__user__school=request.user.school,
    
    )
    total_paid = (
        payment.opening_balance.payments.aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    remaining_balance = (
        payment.opening_balance.amount
        - total_paid
    ) 

    context = {
        "student": payment.opening_balance.student,
        "payment": payment,
        "opening_balance": payment.opening_balance,
        "remaining_balance": remaining_balance,
        "school_settings": SchoolSettings.load(
            payment.opening_balance.student.user.school
        ),
    }

    template = get_template(
        "billing/opening_balance_payment_receipt.html"
    )

    html_string = template.render(
        context,
        request=request,
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="'
        f'opening_balance_receipt_'
        f'{payment.receipt_number}.pdf"'
    )

    HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf(response)

    return response


@login_required
def student_account_statement(request, student_id):
    """
    Read-only allocation-based account statement across all sessions.

    Billing staff can view students in their school.
    Students can only view their own account statement.
    """

    if is_student(request.user):

        student = get_object_or_404(
            Student,
            id=student_id,
            user=request.user,
            user__school=request.user.school,
        )

    else:

        if not can_manage_billing(request.user):
            raise PermissionDenied(
                "You do not have permission to access this account statement."
            )

        student = get_object_or_404(
            Student,
            id=student_id,
            user__school=request.user.school,
        )

    # Deliberately derive paid amounts through get_student_fee_breakdown(),
    # which sums PaymentAllocation records.  Raw Payment amounts are not used:
    # legacy, unallocated payments must not reduce a category or term balance.
    sessions = AcademicSession.objects.filter(
        school=request.user.school,
    ).order_by("id")
    statement_sessions = []
    total_charged = Decimal("0.00")
    total_allocated = Decimal("0.00")

    for session in sessions:
        term_rows = []
        for term in sorted(session.terms.all(), key=get_term_order):
            breakdown = get_student_fee_breakdown(student, term)
            charged = sum((item["amount"] for item in breakdown), Decimal("0.00"))
            allocated = sum((item["paid"] for item in breakdown), Decimal("0.00"))
            balance = sum((item["balance"] for item in breakdown), Decimal("0.00"))

            # Do not add empty terms to a statement.  A paid allocation is
            # included even if its matching fee assignment was later removed.
            allocation_exists = PaymentAllocation.objects.filter(
                payment__student=student,
                payment__term=term,
            ).exists()
            if charged or allocated or allocation_exists:
                term_rows.append({
                    "term": term,
                    "charged": charged,
                    "allocated": allocated,
                    "balance": balance,
                    "breakdown": breakdown,
                })
                total_charged += charged
                total_allocated += allocated

        if term_rows:
            statement_sessions.append({
                "session": session,
                "terms": term_rows,
                "charged": sum((row["charged"] for row in term_rows), Decimal("0.00")),
                "allocated": sum((row["allocated"] for row in term_rows), Decimal("0.00")),
                "arrears": sum((row["balance"] for row in term_rows), Decimal("0.00")),
            })

    # ---------------------------------------------------------
    # OPENING BALANCE
    # ---------------------------------------------------------

    opening_balance = OpeningBalance.objects.filter(
        student=student
    ).first()

    opening_amount = (
        opening_balance.amount
        if opening_balance
        else Decimal("0.00")
    )

    # ---------------------------------------------------------
    # OPENING BALANCE PAYMENTS
    # ---------------------------------------------------------

    opening_paid = Decimal("0.00")

    if opening_balance:

        opening_paid = (
            opening_balance.payments.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

    # ---------------------------------------------------------
    # OPENING BALANCE REMAINING
    # ---------------------------------------------------------

    opening_arrears = (
        opening_amount - opening_paid
    )

    # Prevent negative balance in case of legacy/incorrect data.

    if opening_arrears < Decimal("0.00"):

        opening_arrears = Decimal("0.00")

    # ---------------------------------------------------------
    # TERM ARREARS
    # ---------------------------------------------------------

    term_arrears = sum(
        (
            session_row["arrears"]
            for session_row in statement_sessions
        ),
        Decimal("0.00"),
    )

    # ---------------------------------------------------------
    # TOTAL ACCOUNT ARREARS
    # ---------------------------------------------------------

    account_arrears = (
        term_arrears
        + opening_arrears
    )

    return render(
        request,
        "billing/student_account_statement.html",
        {
            "student": student,
            "statement_sessions": statement_sessions,
            "total_charged": total_charged,
            "total_allocated": total_allocated,
            "term_arrears": term_arrears,

            "opening_balance": opening_balance,
            "opening_amount": opening_amount,
            "opening_paid": opening_paid,
            "opening_arrears": opening_arrears,

            "account_arrears": account_arrears,
        },
    )
    
@login_required
@billing_required
def select_student_account_statement(request):

    school = request.user.school

    students = Student.objects.filter(
        user__school=school,
        is_active=True,
    ).select_related(
        "user",
        "school_class",
    ).order_by(
        "school_class__name",
        "user__last_name",
        "user__first_name",
    )

    query = request.GET.get("q", "").strip()

    if query:
        students = students.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(admission_number__icontains=query)
        )

    return render(
        request,
        "billing/select_student_account_statement.html",
        {
            "students": students,
            "query": query,
        },
    )
    
@login_required
def my_payment_history(request):
    """
    Student-facing payment history.

    A student can only see payments belonging to their own
    student account.
    """

    student = get_object_or_404(
        Student,
        user=request.user,
        user__school=request.user.school,
    )

    payments = (
        Payment.objects
        .filter(
            student=student,
            student__user__school=request.user.school,
        )
        .select_related(
            "term",
            "recorded_by",
        )
        .order_by(
            "-date_paid",
            "-id",
        )
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
            "is_student_portal": True,
        }
    )
    
