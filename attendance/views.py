from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import datetime

from accounts.decorators import staff_required
from accounts.permissions import is_management
from accounts.utils import get_teacher
from students.models import Student, SchoolClass
from .models import AttendanceRecord


@staff_required
@login_required
def select_class_for_attendance(request):
    teacher = get_teacher(request.user)

    if is_management(request.user):
        classes = SchoolClass.objects.filter(
            school=request.user.school
        )

    elif teacher and teacher.is_class_teacher and teacher.assigned_class:
        classes = SchoolClass.objects.filter(
            id=teacher.assigned_class_id,
            school=request.user.school,
        )

    else:
        raise PermissionDenied(
            "Only class teachers, principals, or admins can mark attendance."
        )

    return render(
        request,
        "attendance/select_class.html",
        {
            "classes": classes,
        },
    )


@staff_required
@login_required
def mark_attendance(request, class_id):
    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=request.user.school,
    )

    teacher = get_teacher(request.user)

    if not is_management(request.user):
        if not (
            teacher
            and teacher.is_class_teacher
            and teacher.assigned_class_id == school_class.id
        ):
            raise PermissionDenied(
                "You can only mark attendance for your own class."
            )

    date_str = request.GET.get("date") or request.POST.get("date")

    try:
        selected_date = (
            datetime.date.fromisoformat(date_str)
            if date_str
            else datetime.date.today()
        )
    except ValueError:
        raise PermissionDenied("Invalid attendance date.")

    is_weekend = selected_date.weekday() >= 5

    students = Student.objects.filter(
        school_class=school_class,
        is_active=True,
    )

    if request.method == "POST":
        if is_weekend:
            return redirect(
                f"/attendance/mark/{school_class.id}/?date={selected_date}"
            )

        for student in students:
            is_present = request.POST.get(
                f"present_{student.id}"
            ) == "on"

            AttendanceRecord.objects.update_or_create(
                student=student,
                date=selected_date,
                defaults={
                    "is_present": is_present,
                    "marked_by": request.user,
                },
            )

        return redirect(
            f"/attendance/mark/{school_class.id}/?date={selected_date}"
        )

    existing = {
        record.student_id: record.is_present
        for record in AttendanceRecord.objects.filter(
            student__in=students,
            date=selected_date,
        )
    }

    student_rows = [
        (student, existing.get(student.id, True))
        for student in students
    ]

    return render(
        request,
        "attendance/mark_attendance.html",
        {
            "school_class": school_class,
            "selected_date": selected_date,
            "student_rows": student_rows,
            "is_weekend": is_weekend,
        },
    )


@staff_required
@login_required
def class_attendance_summary(request):
    class_id = request.GET.get("class")
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    teacher = get_teacher(request.user)

    if is_management(request.user):
        classes = SchoolClass.objects.filter(
            school=request.user.school
        )

    elif teacher and teacher.is_class_teacher and teacher.assigned_class:
        classes = SchoolClass.objects.filter(
            id=teacher.assigned_class_id,
            school=request.user.school,
        )

    else:
        raise PermissionDenied(
            "Only class teachers, principals, or admins can view this report."
        )

    rows = []
    selected_class = None

    try:
        start_date = (
            datetime.date.fromisoformat(start_str)
            if start_str
            else None
        )

        end_date = (
            datetime.date.fromisoformat(end_str)
            if end_str
            else None
        )

    except ValueError:
        raise PermissionDenied("Invalid attendance date range.")

    if class_id:
        selected_class = get_object_or_404(
            SchoolClass,
            id=class_id,
            school=request.user.school,
        )

        if not is_management(request.user):
            if (
                not teacher
                or not teacher.is_class_teacher
                or teacher.assigned_class_id != selected_class.id
            ):
                raise PermissionDenied(
                    "You can only view attendance for your own class."
                )

        students = Student.objects.filter(
            school_class=selected_class,
            is_active=True,
        )

        for student in students:
            records = AttendanceRecord.objects.filter(
                student=student,
            )

            if start_date:
                records = records.filter(
                    date__gte=start_date
                )

            if end_date:
                records = records.filter(
                    date__lte=end_date
                )

            days_marked = records.count()

            days_present = records.filter(
                is_present=True
            ).count()

            percentage = (
                round(
                    (days_present / days_marked) * 100,
                    1,
                )
                if days_marked
                else None
            )

            rows.append(
                {
                    "student": student,
                    "days_marked": days_marked,
                    "days_present": days_present,
                    "percentage": percentage,
                }
            )

    return render(
        request,
        "attendance/class_summary.html",
        {
            "classes": classes,
            "selected_class": selected_class,
            "start_date": start_date,
            "end_date": end_date,
            "rows": rows,
        },
    )