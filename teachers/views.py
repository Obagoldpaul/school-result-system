from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
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
    teachers = Teacher.objects.filter(is_active=True)
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers})

from django.shortcuts import get_object_or_404
from students.models import SchoolClass


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