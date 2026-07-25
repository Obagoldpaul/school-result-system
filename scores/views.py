from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from allocations.models import SubjectAllocation
from students.models import Student
from .models import Score


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