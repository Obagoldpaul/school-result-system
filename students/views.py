from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm


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
    from .models import Student
    students = Student.objects.filter(is_active=True)
    return render(request, 'students/student_list.html', {'students': students})