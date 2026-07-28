from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from students.models import Student
from teachers.models import Teacher
from subjects.models import Subject
from students.models import SchoolClass
from academics.models import Term
from allocations.models import SubjectAllocation


@login_required
def home(request):
    context = {
        'student_count': Student.objects.filter(is_active=True).count(),
        'teacher_count': Teacher.objects.filter(is_active=True).count(),
        'subject_count': Subject.objects.filter(is_active=True).count(),
        'class_count': SchoolClass.objects.count(),
        'allocation_count': SubjectAllocation.objects.count(),
        'current_term': Term.objects.filter(is_current=True).first(),
    }

    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile:
        context['my_allocations'] = SubjectAllocation.objects.filter(teacher=teacher_profile)

    return render(request, 'dashboard/home.html', context)