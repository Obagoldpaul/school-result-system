from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from allocations.models import SubjectAllocation
from students.models import Student
from .models import Score
from .models import get_report_card_rows
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import get_template
import os
from django.conf import settings


def link_callback(uri, rel):
    """Convert HTML URIs to absolute system paths so xhtml2pdf can find images/CSS."""
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATICFILES_DIRS[0], uri.replace(settings.STATIC_URL, ""))
    else:
        return uri
    if not os.path.isfile(path):
        raise Exception(f'Static file not found: {path}')
    return path

@login_required
def select_allocation(request):
    """Step 1: teacher picks which class/subject/term they want to enter scores for."""
    teacher = getattr(request.user, 'teacher_profile', None)
    if teacher:
        allocations = SubjectAllocation.objects.filter(teacher=teacher)
    else:
        allocations = SubjectAllocation.objects.all()  # admin can see all
    return render(request, 'scores/select_allocation.html', {'allocations': allocations})


@login_required
def enter_scores(request, allocation_id):
    """Step 2: show all students in that class, let teacher enter CA + Exam for each."""
    allocation = get_object_or_404(SubjectAllocation, id=allocation_id)
    students = Student.objects.filter(school_class=allocation.school_class, is_active=True)

    if request.method == 'POST':
        for student in students:
            ca = request.POST.get(f'ca_{student.id}')
            exam = request.POST.get(f'exam_{student.id}')
            if ca is not None and exam is not None:
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

    # Pre-fill existing scores if any
    existing_scores = {
        s.student_id: s for s in Score.objects.filter(
            subject=allocation.subject, term=allocation.term, student__in=students
        )
    }
    student_score_pairs = [(student, existing_scores.get(student.id)) for student in students]

    return render(request, 'scores/enter_scores.html', {
        'allocation': allocation,
        'student_score_pairs': student_score_pairs,
    })


from students.models import SchoolClass
from academics.models import Term
from .models import get_class_results


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


from .forms import ReportCardExtraForm
from .models import ReportCardExtra


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
    rows = get_report_card_rows(student, term)
    extra = ReportCardExtra.objects.filter(student=student, term=term).first()

    total = sum(row['total_score'] for row in rows)
    subject_count = len(rows)
    average = round(total / subject_count, 2) if subject_count else 0
    marks_obtainable = subject_count * 100
    percentage = round((total / marks_obtainable) * 100, 1) if marks_obtainable else 0

    class_results = get_class_results(student.school_class, term)
    position = next((r['position'] for r in class_results if r['student'].id == student.id), '-')

    return render(request, 'scores/report_card.html', {
        'student': student,
        'term': term,
        'rows': rows,
        'extra': extra,
        'total': total,
        'average': average,
        'position': position,
        'marks_obtainable': marks_obtainable,
        'percentage': percentage,
    })



@login_required
def report_card_pdf(request, student_id, term_id):
    student = get_object_or_404(Student, id=student_id)
    term = get_object_or_404(Term, id=term_id)
    rows = get_report_card_rows(student, term)
    extra = ReportCardExtra.objects.filter(student=student, term=term).first()

    total = sum(row['total_score'] for row in rows)
    subject_count = len(rows)
    average = round(total / subject_count, 2) if subject_count else 0
    marks_obtainable = subject_count * 100
    percentage = round((total / marks_obtainable) * 100, 1) if marks_obtainable else 0

    class_results = get_class_results(student.school_class, term)
    position = next((r['position'] for r in class_results if r['student'].id == student.id), '-')

    template = get_template('scores/report_card_pdf.html')
    html = template.render({
        'student': student,
        'term': term,
        'rows': rows,
        'extra': extra,
        'total': total,
        'average': average,
        'position': position,
        'marks_obtainable': marks_obtainable,
        'percentage': percentage,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{student.admission_number}_report_card.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    if pisa_status.err:
        return HttpResponse('We had some errors generating the PDF <pre>' + html + '</pre>')
    return response