from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML

from accounts.decorators import staff_required
from accounts.utils import get_teacher, get_student, get_current_term
from allocations.models import SubjectAllocation
from students.models import Student, SchoolClass
from academics.models import Term
from .models import Score, ReportCardExtra, get_class_results
from .forms import ReportCardExtraForm
from . import services


@staff_required
@login_required
def select_allocation(request):
    teacher = get_teacher(request.user)
    if teacher:
        allocations = SubjectAllocation.objects.filter(teacher=teacher)
    else:
        allocations = SubjectAllocation.objects.all()

    class_id = request.GET.get('class')
    term_id = request.GET.get('term')
    subject_id = request.GET.get('subject')
    status = request.GET.get('status')

    if class_id:
        allocations = allocations.filter(school_class_id=class_id)
    if term_id:
        allocations = allocations.filter(term_id=term_id)
    if subject_id:
        allocations = allocations.filter(subject_id=subject_id)
    if status:
        allocations = allocations.filter(status=status)

    from subjects.models import Subject

    context = {
        'allocations': allocations.select_related('teacher', 'subject', 'school_class', 'term'),
        'classes': SchoolClass.objects.all(),
        'terms': Term.objects.all(),
        'subjects': Subject.objects.all(),
        'status_choices': SubjectAllocation.Status.choices,
        'selected_class': class_id,
        'selected_term': term_id,
        'selected_subject': subject_id,
        'selected_status': status,
        'current_query': request.GET.urlencode(),
    }
    return render(request, 'scores/select_allocation.html', context)


@staff_required
@login_required
def enter_scores(request, allocation_id):
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    services.check_allocation_ownership(request.user, allocation)
    can_edit = services.can_edit_allocation(request.user, allocation)

    students = Student.objects.filter(school_class=allocation.school_class, is_active=True)
    if allocation.subject.is_elective:
        students = students.filter(elective_subjects=allocation.subject)

    if request.method == 'POST':
        if not can_edit:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Scores can only be edited while status is Draft.")
        for student in students:
            ca = request.POST.get(f'ca_{student.id}', '').strip()
            exam = request.POST.get(f'exam_{student.id}', '').strip()
            if ca or exam:
                Score.objects.update_or_create(
                    student=student,
                    subject=allocation.subject,
                    term=allocation.term,
                    defaults={
                        'ca_score': ca or 0,
                        'exam_score': exam or 0,
                        'recorded_by': allocation.teacher,
                    }
                )
        return redirect('select_allocation')

    existing_scores = {
        s.student_id: s for s in Score.objects.filter(
            subject=allocation.subject, term=allocation.term, student__in=students
        )
    }
    student_score_pairs = [(student, existing_scores.get(student.id)) for student in students]

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
def submit_allocation(request, allocation_id):
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    services.check_allocation_ownership(request.user, allocation)
    services.submit_allocation_for_review(allocation)
    return _redirect_with_query(request)


@staff_required
@login_required
def review_allocation(request, allocation_id):
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)

    if request.method == 'POST':
        services.mark_allocation_reviewed(allocation, request.POST.get('comment', ''))
        return _redirect_with_query(request)

    return render(request, 'scores/review_allocation.html', {'allocation': allocation})


@staff_required
@login_required
def approve_allocation(request, allocation_id):
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    services.approve_allocation_results(allocation)
    return _redirect_with_query(request)


@staff_required
@login_required
def publish_allocation(request, allocation_id):
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    services.publish_allocation_results(allocation)
    return _redirect_with_query(request)


@staff_required
@login_required
def class_results(request):
    classes = SchoolClass.objects.all()
    terms = Term.objects.all()
    results = None
    selected_class = None
    selected_term = None

    class_id = request.GET.get('class')
    term_id = request.GET.get('term')

    if class_id and term_id:
        selected_class = get_object_or_404(SchoolClass, id=class_id)
        selected_term = get_object_or_404(Term, id=term_id)
        results = get_class_results(selected_class, selected_term)

    return render(request, 'scores/class_results.html', {
        'classes': classes,
        'terms': terms,
        'results': results,
        'selected_class': selected_class,
        'selected_term': selected_term,
    })


@staff_required
@login_required
def edit_report_extra(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    extra, created = ReportCardExtra.objects.get_or_create(student=student, term=term)

    if request.method == 'POST':
        form = ReportCardExtraForm(request.POST, instance=extra)
        if form.is_valid():
            form.save()
            return redirect('report_card', student_id=student.id, term_id=term.id)
    else:
        form = ReportCardExtraForm(instance=extra)

    return render(request, 'scores/edit_report_extra.html', {
        'form': form, 'student': student, 'term': term
    })


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
    student = get_object_or_404(Student, id=student_id)

    student_profile = get_student(request.user)
    if student_profile and student_profile.id != student.id:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You can only view your own report cards.")

    terms = Term.objects.all().order_by('session', 'name')
    return render(request, 'scores/select_report_term.html', {
        'student': student,
        'terms': terms,
    })