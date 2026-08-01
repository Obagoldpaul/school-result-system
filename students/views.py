from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm
from .models import Student, SchoolClass, Department
from accounts.decorators import staff_required, management_required

@management_required
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

@staff_required
@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.school_class_id = request.POST.get('school_class')
        student.department_id = request.POST.get('department') or None
        student.guardian_name = request.POST.get('guardian_name', '')
        student.guardian_phone = request.POST.get('guardian_phone', '')
        student.save()
        elective_ids = request.POST.getlist('electives')
        student.elective_subjects.set(elective_ids)
        return redirect('student_list')

    from subjects.models import Subject
    classes = SchoolClass.objects.all()
    departments = Department.objects.all()
    electives = Subject.objects.filter(is_elective=True)
    return render(request, 'students/edit_student.html', {
        'student': student,
        'classes': classes,
        'departments': departments,
        'electives': electives,
    })