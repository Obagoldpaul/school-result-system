from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from students.models import SchoolClass
from .forms import TeacherRegistrationForm
from .models import Teacher
from accounts.decorators import staff_required, management_required

@management_required
@login_required
def register_teacher(request):

    if request.method == "POST":

        form = TeacherRegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect(
                "teacher_list"
            )

    else:

        form = TeacherRegistrationForm()


    return render(
        request,
        "teachers/register_teacher.html",
        {
            "form": form,
        },
    )




@staff_required
@login_required
def teacher_list(request):

    teachers = Teacher.objects.all()

    search = request.GET.get("search")
    filter_type = request.GET.get("filter")

    if search:
        teachers = teachers.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(staff_id__icontains=search) |
            Q(phone_number__icontains=search)
        )

    if filter_type == "class":
        teachers = teachers.filter(
            is_class_teacher=True
        )

    elif filter_type == "assigned":
        teachers = teachers.exclude(
            assigned_class__isnull=True
        )

    elif filter_type == "inactive":
        teachers = teachers.filter(
            is_active=False
        )

    context = {

        "teachers": teachers,

        "search": search or "",

        "filter": filter_type or "",

        "total_teachers": Teacher.objects.count(),

        "class_teacher_count":
            Teacher.objects.filter(
                is_class_teacher=True
            ).count(),

        "assigned_count":
            Teacher.objects.exclude(
                assigned_class__isnull=True
            ).count(),

        "inactive_count":
            Teacher.objects.filter(
                is_active=False
            ).count(),
    }

    return render(
        request,
        "teachers/teacher_list.html",
        context
    )




@management_required
@login_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)

    if request.method == 'POST':
        teacher.qualification = request.POST.get('qualification', '')
        teacher.phone_number = request.POST.get('phone_number', '')
        teacher.is_class_teacher = request.POST.get('is_class_teacher') == 'on'
        assigned_class_id = request.POST.get('assigned_class')
        teacher.assigned_class_id = assigned_class_id or None
        teacher.save()
        return redirect('teacher_list')

    classes = SchoolClass.objects.all()
    return render(request, 'teachers/edit_teacher.html', {
        'teacher': teacher,
        'classes': classes,
    })
    
@staff_required
@login_required
def teacher_profile(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    return render(
        request,
        "teachers/teacher_profile.html",
        {
            "teacher": teacher,
        },
    )
    
@management_required
@login_required
def deactivate_teacher(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    teacher.is_active = False
    teacher.save()

    return redirect("teacher_list")


@management_required
@login_required
def activate_teacher(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    teacher.is_active = True
    teacher.save()

    return redirect("teacher_list")

@staff_required
@login_required
def print_teacher_profile(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    return render(
        request,
        "teachers/print_teacher_profile.html",
        {
            "teacher": teacher,
        },
    )