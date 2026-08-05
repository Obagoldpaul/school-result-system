from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import StudentRegistrationForm
from .models import Student, SchoolClass, Department
from accounts.decorators import staff_required, management_required
from django.db import models

@management_required
@login_required
def register_student(request):
    if request.method == "POST":
        form = StudentRegistrationForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            form.save()
            return redirect("student_list")

    else:
        form = StudentRegistrationForm()

    print(form)
    print(form["lin"])

    return render(
        request,
        "students/register_student.html",
        {
            "form": form,
            "student_list_url": "/students/",
        },
    )

@login_required
def student_list(request):

    students = Student.objects.filter(
        is_active=True
    ).select_related(
        "user",
        "school_class",
        "department"
    )

    class_id = request.GET.get("class")

    if class_id:
        students = students.filter(
            school_class_id=class_id
        )

    search = request.GET.get("search")

    if search:

        students = students.filter(
            user__first_name__icontains=search
        ) | students.filter(
            user__last_name__icontains=search
        ) | students.filter(
            admission_number__icontains=search
        ) | students.filter(
            lin__icontains=search
        )

    classes = SchoolClass.objects.all().order_by("name")

    return render(
        request,
        "students/student_list.html",
        {
            "students": students,
            "classes": classes,
            "selected_class": int(class_id) if class_id else None,
            "search": search,
        },
    )

@management_required
@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.user.first_name = request.POST.get('first_name', '')
        student.user.other_name = request.POST.get('other_name', '')
        student.user.last_name = request.POST.get('last_name', '')
        student.user.save()

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

@management_required
@login_required
def promote_class(request):
    classes = SchoolClass.objects.all()

    if request.method == 'POST':
        from_class_id = request.POST.get('from_class')
        to_class_id = request.POST.get('to_class')
        if from_class_id and to_class_id and from_class_id != to_class_id:
            students = Student.objects.filter(school_class_id=from_class_id, is_active=True)
            count = students.update(school_class_id=to_class_id)
            return render(request, 'students/promote_result.html', {
                'count': count,
                'from_class': SchoolClass.objects.get(id=from_class_id),
                'to_class': SchoolClass.objects.get(id=to_class_id),
            })

    return render(request, 'students/promote_class.html', {'classes': classes})

@login_required
def student_profile(request, student_id):

    student = get_object_or_404(
        Student.objects.select_related(
            "user",
            "school_class",
            "department",
        ),
        id=student_id,
    )

    return render(
        request,
        "students/student_profile.html",
        {
            "student": student,
        },
    )