from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import datetime

from accounts.decorators import staff_required
from accounts.permissions import is_management, is_class_teacher
from accounts.utils import get_teacher
from students.models import Student, SchoolClass
from .models import AttendanceRecord


@staff_required
@login_required
def select_class_for_attendance(request):
    teacher = get_teacher(request.user)
    if is_management(request.user):
        classes = SchoolClass.objects.all()
    elif teacher and teacher.is_class_teacher and teacher.assigned_class:
        classes = SchoolClass.objects.filter(id=teacher.assigned_class_id)
    else:
        raise PermissionDenied("Only class teachers, principals, or admins can mark attendance.")

    return render(request, 'attendance/select_class.html', {'classes': classes})


@staff_required
@login_required
def mark_attendance(request, class_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)

    teacher = get_teacher(request.user)
    if not is_management(request.user):
        if not (teacher and teacher.is_class_teacher and teacher.assigned_class_id == school_class.id):
            raise PermissionDenied("You can only mark attendance for your own class.")

    date_str = request.GET.get('date') or request.POST.get('date')
    selected_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()

    is_weekend = selected_date.weekday() >= 5  # 5 = Saturday, 6 = Sunday
    

    students = Student.objects.filter(school_class=school_class, is_active=True)

    if request.method == 'POST':
        if is_weekend:
            return redirect(f'/attendance/mark/{school_class.id}/?date={selected_date}')
        for student in students:
            is_present = request.POST.get(f'present_{student.id}') == 'on'
            AttendanceRecord.objects.update_or_create(
                student=student,
                date=selected_date,
                defaults={'is_present': is_present, 'marked_by': request.user}
            )
        return redirect(f'/attendance/mark/{school_class.id}/?date={selected_date}')

    existing = {
        r.student_id: r.is_present for r in AttendanceRecord.objects.filter(
            student__in=students, date=selected_date
        )
    }
    student_rows = [(s, existing.get(s.id, True)) for s in students]

    return render(request, 'attendance/mark_attendance.html', {
        'school_class': school_class,
        'selected_date': selected_date,
        'student_rows': student_rows,
        'is_weekend': is_weekend,
    })