from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import TeacherRegistrationForm
from .models import Teacher
from accounts.decorators import staff_required, management_required

@management_required
@login_required
def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('teacher_list')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'teachers/register_teacher.html', {
        'form': form,
        'teacher_list_url': '/teachers/',
    })

@staff_required
@login_required
def teacher_list(request):
    teachers = Teacher.objects.filter(is_active=True)
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers})