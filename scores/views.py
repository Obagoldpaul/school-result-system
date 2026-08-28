from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML

from django.contrib import messages
from .exceptions import ScoreValidationError
from accounts.decorators import staff_required, feature_required
from accounts.utils import get_teacher, get_student, get_current_term
from allocations.models import SubjectAllocation
from students.models import Student, SchoolClass
from academics.models import AcademicSession, Term
from .models import Score, ReportCardExtra
from .reports import get_class_results
from .forms import ReportCardExtraForm
from . import services
from accounts.permissions import (
    school_permission_required,
    user_has_permission,
    can_edit_report_extra,
)
from django.core.exceptions import PermissionDenied



@staff_required
@login_required
@school_permission_required("scores.view")
def select_allocation(request):
    school = request.user.school

    teacher = get_teacher(request.user)

    if teacher:
        allocations = SubjectAllocation.objects.filter(
            teacher=teacher,
            school_class__school=school,
        )
    else:
        allocations = SubjectAllocation.objects.filter(
            school_class__school=school,
        )

    class_id = request.GET.get('class')
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')

    # ---------------------------------------------------------
    # SESSION
    # ---------------------------------------------------------

    from academics.models import AcademicSession

    selected_session = None

    if session_id:
        selected_session = AcademicSession.objects.filter(
            id=session_id,
            school=school,
        ).first()

        if not selected_session:
            session_id = None

    # ---------------------------------------------------------
    # TERMS
    # ---------------------------------------------------------

    terms = Term.objects.filter(
        session__school=school
    ).select_related(
        'session'
    )

    if selected_session:
        terms = terms.filter(
            session=selected_session
        )

    terms = terms.order_by(
        '-session__name',
        'name',
    )

    # ---------------------------------------------------------
    # SELECTED TERM
    # ---------------------------------------------------------

    if term_id:
        selected_term_obj = terms.filter(
            id=term_id
        ).first()

        if selected_term_obj:
            term_id = str(selected_term_obj.id)
        else:
            selected_term_obj = None
            term_id = None
    else:
        selected_term_obj = None

        # Preserve the existing behaviour of using the
        # current term when no term is selected.
        current_term = get_current_term(request.user)

        if current_term:
            if selected_session:
                if current_term.session_id == selected_session.id:
                    selected_term_obj = current_term
                    term_id = str(current_term.id)
            else:
                selected_term_obj = current_term
                term_id = str(current_term.id)

    # ---------------------------------------------------------
    # FILTER ALLOCATIONS
    # ---------------------------------------------------------

    if class_id:
        allocations = allocations.filter(
            school_class_id=class_id,
            school_class__school=school,
        )

    if term_id:
        allocations = allocations.filter(
            term_id=term_id
        )

    if subject_id:
        allocations = allocations.filter(
            subject_id=subject_id
        )

    if status:
        allocations = allocations.filter(
            status=status
        )

    from subjects.models import Subject

    allocations = allocations.select_related(
        'teacher',
        'subject',
        'school_class',
        'term',
    )

    classes = SchoolClass.objects.filter(
        school=school
    )

    # ---------------------------------------------------------
    # GROUP ALLOCATIONS BY CLASS
    # ---------------------------------------------------------

    grouped = []

    for c in classes:
        class_allocations = [
            a for a in allocations
            if a.school_class_id == c.id
        ]

        if class_allocations:
            grouped.append({
                'school_class': c,
                'allocations': class_allocations,
            })

    # ---------------------------------------------------------
    # SESSIONS
    # ---------------------------------------------------------

    sessions = AcademicSession.objects.filter(
        school=school
    ).order_by(
        '-name'
    )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        'grouped': grouped,
        'classes': classes,

        'sessions': sessions,
        'selected_session': selected_session,

        'terms': terms,

        'subjects': Subject.objects.filter(
            school=school,
            is_active=True,
        ),

        'status_choices': SubjectAllocation.Status.choices,

        'selected_class': class_id,
        'selected_term': term_id,
        'selected_subject': subject_id,
        'selected_status': status,

        'current_query': request.GET.urlencode(),
    }

    return render(
        request,
        'scores/select_allocation.html',
        context
    )


@staff_required
@login_required
@school_permission_required("scores.enter")
def enter_scores(request, allocation_id):
    allocation = get_object_or_404(
        SubjectAllocation,
        id=allocation_id,
        school_class__school=request.user.school,
        )
    services.check_allocation_ownership(request.user, allocation)
    can_edit = services.can_edit_allocation(request.user, allocation)

    students = services.get_students_for_allocation(allocation)

    if request.method == 'POST':
        if not can_edit:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Scores can only be edited while status is Draft.")

        try:
            services.save_scores(
                allocation,
                students,
                request.POST,
            )

            messages.success(
                request,
                "Scores saved successfully."
            )

            return redirect("select_allocation")

        except ScoreValidationError as e:
            messages.error(request, str(e))

    student_score_pairs = services.get_student_score_pairs(
        allocation,
        students,
    )

    return render(request, 'scores/enter_scores.html', {
        'allocation': allocation,
        'student_score_pairs': student_score_pairs,
        'can_edit': can_edit,
    })


def _redirect_with_query(request):
    from django.urls import reverse
    url = reverse('select_allocation')
    query = request.GET.urlencode()
    if query:
        url += f'?{query}'
    return redirect(url)


@staff_required
@login_required
@school_permission_required("scores.submit")
def submit_allocation(request, allocation_id):
    allocation = get_object_or_404(
        SubjectAllocation, 
        id=allocation_id,
        school_class__school=request.user.school,
    )

    services.ensure_can_submit(
        request.user,
        allocation,
    )

    services.submit_allocation_for_review(
        allocation,
        user=request.user,
    )

    return _redirect_with_query(request)


@staff_required
@login_required
@school_permission_required("scores.review")
def review_allocation(request, allocation_id):
    allocation = get_object_or_404(
        SubjectAllocation, 
        id=allocation_id,
        school_class__school=request.user.school,)

    services.ensure_can_review(
        request.user,
        allocation,
    )

    if request.method == 'POST':
        services.mark_allocation_reviewed(
            allocation,
            request.POST.get('comment', ''),
            user=request.user,
        )
        return _redirect_with_query(request)

    return render(
        request,
        'scores/review_allocation.html',
        {
            'allocation': allocation,
        }
    )

@staff_required
@login_required
@school_permission_required("scores.approve")
def approve_allocation(request, allocation_id):
    allocation = get_object_or_404(
        SubjectAllocation,
        id=allocation_id,
        school_class__school=request.user.school,
    )

    services.ensure_can_approve(
        request.user,
        allocation,
    )

    services.approve_allocation_results(
        allocation,
        user=request.user,
    )

    return _redirect_with_query(request)


@staff_required
@login_required
@school_permission_required("scores.publish")
def publish_allocation(request, allocation_id):
    allocation = get_object_or_404(
        SubjectAllocation,
        id=allocation_id,
        school_class__school=request.user.school,
    )

    services.ensure_can_publish(
        request.user,
        allocation,
    )

    services.publish_allocation_results(
        allocation,
        user=request.user,
    )

    return _redirect_with_query(request)


@login_required
@staff_required
@school_permission_required("scores.view")
def class_results(request):
    school = request.user.school

    classes = SchoolClass.objects.filter(
        school=school
    )

    # -------------------------------------------------
    # ACADEMIC SESSIONS
    # -------------------------------------------------

    sessions = AcademicSession.objects.filter(
        school=school
    ).order_by(
        '-name'
    )

    results = None
    selected_class = None
    selected_session = None
    selected_term = None

    class_id = request.GET.get('class')
    session_id = request.GET.get('session')
    term_id = request.GET.get('term')

    # -------------------------------------------------
    # SELECT SESSION
    # -------------------------------------------------

    if session_id:
        selected_session = get_object_or_404(
            AcademicSession,
            id=session_id,
            school=school,
        )

    # -------------------------------------------------
    # TERMS
    #
    # Only show terms belonging to the selected
    # academic session.
    # -------------------------------------------------

    if selected_session:
        terms = Term.objects.filter(
            session=selected_session,
            session__school=school,
        ).order_by(
            'name'
        )
    else:
        terms = Term.objects.none()

    # -------------------------------------------------
    # SELECT CLASS + TERM
    # -------------------------------------------------

    if class_id and session_id and term_id:

        selected_class = get_object_or_404(
            SchoolClass,
            id=class_id,
            school=school,
        )

        # The term MUST belong to the selected session
        # and the current school.
        selected_term = get_object_or_404(
            Term,
            id=term_id,
            session=selected_session,
            session__school=school,
        )

        # -------------------------------------------------
        # EXISTING RESULT CALCULATION
        #
        # Leave this completely unchanged.
        # -------------------------------------------------

        results = get_class_results(
            selected_class,
            selected_term,
        )

    return render(
        request,
        'scores/class_results.html',
        {
            'classes': classes,
            'sessions': sessions,
            'terms': terms,
            'results': results,
            'selected_class': selected_class,
            'selected_session': selected_session,
            'selected_term': selected_term,
        }
    )


@staff_required
@login_required
def edit_report_extra(request, student_id, term_id):
    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school,
    )

    term = get_object_or_404(
        Term,
        id=term_id,
        session__school=request.user.school,
    )
    
    
    if not  can_edit_report_extra(
        request.user,
        student,
    ):
        raise PermissionDenied(
            "You do not have permission to edit this student's report details."
        )
        
    has_teacher_remark_permission = user_has_permission(
        request.user,
        "reports.teacher_remark",
    )
    
    has_principal_remark_permission = user_has_permission(
            request.user,
            "reports.principal_remark",
    )
    
    if not (
        has_teacher_remark_permission
        or has_principal_remark_permission
    ):
        raise PermissionDenied(
            "You do not have permission to edit report-card details."
        )
    
    extra, created = ReportCardExtra.objects.get_or_create(
        student=student,
        term=term,
    )

    if request.method == 'POST':
        form = ReportCardExtraForm(
            request.POST,
            instance=extra,
            user=request.user,
        )

        if form.is_valid():
            form.save()

            return redirect(
                'report_card',
                student_id=student.id,
                term_id=term.id,
            )

    else:
        form = ReportCardExtraForm(
            instance=extra,
            user=request.user,
        )

    return render(
        request,
        'scores/edit_report_extra.html',
        {
            'form': form,
            'student': student,
            'term': term,
        }
    )


@login_required
def report_card(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    services.check_report_card_access(request.user, student, term)

    extra = ReportCardExtra.objects.filter(student=student, term=term).first()
    context = services.build_report_card_context(student, term)
    context.update({'student': student, 'term': term, 'extra': extra})

    return render(request, 'scores/report_card.html', context)


@login_required
@feature_required("ADVANCED_REPORTING")
@school_permission_required("reports.view")
def report_card_pdf(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    services.check_report_card_access(request.user, student, term)

    extra = ReportCardExtra.objects.filter(student=student, term=term).first()
    context = services.build_report_card_context(student, term)
    context.update({'student': student, 'term': term, 'extra': extra})

    template = get_template('scores/report_card.html')
    html_string = template.render(context, request=request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.admission_number}_report_card.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(response)
    return response


@login_required
def select_report_term(request, student_id):
    student = get_object_or_404(
        Student,
        id=student_id,
        user__school=request.user.school,
    )

    student_profile = get_student(request.user)
    if student_profile and student_profile.id != student.id:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You can only view your own report cards.")

    terms = Term.objects.filter(
        session__school=student.school
    ).order_by(
        'session',
        'name'
    )
    return render(request, 'scores/select_report_term.html', {
        'student': student,
        'terms': terms,
    })