from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm
from .models import Student, SchoolClass


@login_required
def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentRegistrationForm()
    return render(request, 'students/register_student.html', {'form': form})


@login_required
def student_list(request):
    students = Student.objects.filter(is_active=True)
    class_id = request.GET.get('class')
    if class_id:
        students = students.filter(school_class_id=class_id)
    classes = SchoolClass.objects.all()
    return render(request, 'students/student_list.html', {
        'students': students,
        'classes': classes,
        'selected_class': int(class_id) if class_id else None,
    })