from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from students.models import Student, SchoolClass
from teachers.models import Teacher
from subjects.models import Subject
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
    student_profile = getattr(request.user, 'student_profile', None)
    Status = SubjectAllocation.Status

    if teacher_profile:
        context['my_allocations'] = SubjectAllocation.objects.filter(teacher=teacher_profile)
        context['my_draft_count'] = context['my_allocations'].filter(status=Status.DRAFT).count()

        if teacher_profile.is_class_teacher:
            context['pending_review'] = SubjectAllocation.objects.filter(
                school_class=teacher_profile.assigned_class,
                status=Status.SUBMITTED
            )

    if request.user.role in ['ADMIN', 'PRINCIPAL'] or request.user.is_superuser:
        context['pending_approval'] = SubjectAllocation.objects.filter(status=Status.REVIEWED)
        context['pending_publish'] = SubjectAllocation.objects.filter(status=Status.APPROVED)

    if student_profile:
        context['my_student_id'] = student_profile.id

    return render(request, 'dashboard/home.html', context)