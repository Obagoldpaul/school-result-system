from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import datetime

from accounts.decorators import staff_required, feature_required
from accounts.permissions import (
    is_management,
    school_permission_required,
)
from accounts.utils import get_teacher
from students.models import Student, SchoolClass
from .models import AttendanceRecord
from accounts.utils import get_current_term


@staff_required
@login_required
@school_permission_required("attendance.mark")
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
@school_permission_required("attendance.mark")
def mark_attendance(request, class_id):

    school_class = get_object_or_404(
        SchoolClass,
        id=class_id,
        school=request.user.school,
    )

    teacher = get_teacher(request.user)

    # ---------------------------------------------------------
    # PERMISSION CHECK
    # ---------------------------------------------------------

    if not is_management(request.user):

        if not (
            teacher
            and teacher.is_class_teacher
            and teacher.assigned_class_id == school_class.id
        ):
            raise PermissionDenied(
                "You can only mark attendance for your own class."
            )

    # ---------------------------------------------------------
    # SELECT DATE
    # ---------------------------------------------------------

    date_str = (
        request.GET.get("date")
        or request.POST.get("date")
    )

    try:

        selected_date = (
            datetime.date.fromisoformat(date_str)
            if date_str
            else datetime.date.today()
        )

    except ValueError:

        raise PermissionDenied(
            "Invalid attendance date."
        )

    # ---------------------------------------------------------
    # WEEKEND CHECK
    # ---------------------------------------------------------

    is_weekend = selected_date.weekday() >= 5

    # ---------------------------------------------------------
    # GET ACTIVE STUDENTS
    # ---------------------------------------------------------

    students = Student.objects.filter(
        school_class=school_class,
        is_active=True,
    ).order_by(
        "user__last_name",
        "user__first_name",
    )

    # ---------------------------------------------------------
    # SAVE ATTENDANCE
    # ---------------------------------------------------------

    if request.method == "POST":

        if is_weekend:

            return redirect(
                f"/attendance/mark/{school_class.id}/"
                f"?date={selected_date}"
            )

        for student in students:

            status = request.POST.get(
                f"attendance_{student.id}"
            )

            # -------------------------------------------------
            # Only save explicitly selected statuses.
            #
            # If a student is left unmarked, we do NOT create
            # an attendance record.
            # -------------------------------------------------

            if status not in ["present", "absent"]:
                continue

            AttendanceRecord.objects.update_or_create(

                student=student,

                date=selected_date,

                defaults={
                    "is_present": (
                        status == "present"
                    ),
                    "marked_by": request.user,
                },
            )

        return redirect(
            f"/attendance/mark/{school_class.id}/"
            f"?date={selected_date}"
        )

    # ---------------------------------------------------------
    # LOAD EXISTING ATTENDANCE
    # ---------------------------------------------------------

    existing = {

        record.student_id: record.is_present

        for record in AttendanceRecord.objects.filter(
            student__in=students,
            date=selected_date,
        )
    }

    # ---------------------------------------------------------
    # PREPARE STUDENT ROWS
    # ---------------------------------------------------------

    student_rows = []

    for student in students:

        if student.id not in existing:

            status = "not_marked"

        elif existing[student.id]:

            status = "present"

        else:

            status = "absent"

        student_rows.append(
            (
                student,
                status,
            )
        )

    # ---------------------------------------------------------
    # ATTENDANCE SUMMARY FOR SELECTED DATE
    # ---------------------------------------------------------

    total_students = students.count()

    marked_count = len(existing)

    present_count = sum(
        1
        for value in existing.values()
        if value
    )

    absent_count = sum(
        1
        for value in existing.values()
        if not value
    )

    return render(
        request,

        "attendance/mark_attendance.html",

        {
            "school_class": school_class,

            "selected_date": selected_date,

            "student_rows": student_rows,

            "is_weekend": is_weekend,

            "total_students": total_students,

            "marked_count": marked_count,

            "present_count": present_count,

            "absent_count": absent_count,

            "unmarked_count": (
                total_students - marked_count
            ),
        },
    )



@staff_required
@login_required
@school_permission_required("attendance.view")
@feature_required("ADVANCED_ATTENDANCE")
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
    
    total_students = 0
    students_marked = 0
    total_present_records = 0
    total_absent_records = 0
    overall_percentage = None

    # ---------------------------------------------------------
    # CURRENT TERM
    # ---------------------------------------------------------

    current_term = get_current_term(
        request.user
    )

    # ---------------------------------------------------------
    # DATE RANGE
    # ---------------------------------------------------------

    try:

        if start_str:

            start_date = datetime.date.fromisoformat(
                start_str
            )

        elif (
            current_term
            and current_term.start_date
        ):

            start_date = current_term.start_date

        else:

            start_date = None


        if end_str:

            end_date = datetime.date.fromisoformat(
                end_str
            )

        elif (
            current_term
            and current_term.end_date
        ):

            end_date = current_term.end_date

        else:

            end_date = None


    except ValueError:

        raise PermissionDenied(
            "Invalid attendance date range."
        )

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
        total_students = students.count()

        total_present_records = 0
        total_absent_records = 0
        students_marked = 0

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
            
            days_absent = records.filter(
                is_present=False
            ).count()

            if days_marked:
                students_marked += 1

            total_present_records += days_present
            total_absent_records += days_absent

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
            
            # ---------------------------------------------------------
            # CLASS ATTENDANCE TOTALS
            # ---------------------------------------------------------
            
        total_records = (
            total_present_records
            + total_absent_records
        )

        overall_percentage = (
            round(
                 (total_present_records / total_records) * 100,
                1,
            )
            if total_records
            else None
        )

    return render(
        request,
        "attendance/class_summary.html",
        {
            "classes": classes,
            "selected_class": selected_class,
            "start_date": start_date,
            "end_date": end_date,
            "current_term": current_term,
            "rows": rows,
            
            "total_students": total_students,
            "students_marked": students_marked,
            "total_present_records": total_present_records,
            "total_absent_records": total_absent_records,
            "overall_percentage": overall_percentage,
        },
    )
    
@login_required
@feature_required("STUDENT_PORTAL")
def student_attendance_history(request):

    student = getattr(
        request.user,
        "student_profile",
        None,
    )

    if not student:
        raise PermissionDenied(
            "Only students can view attendance history."
        )

    # ---------------------------------------------------------
    # CURRENT TERM
    # ---------------------------------------------------------

    current_term = get_current_term(
        request.user
    )

    records = AttendanceRecord.objects.filter(
        student=student,
    )

    # ---------------------------------------------------------
    # LIMIT HISTORY TO CURRENT TERM
    # ---------------------------------------------------------

    if (
        current_term
        and current_term.start_date
        and current_term.end_date
    ):

        records = records.filter(
            date__gte=current_term.start_date,
            date__lte=current_term.end_date,
        )

    records = records.order_by(
        "-date"
    )

    # ---------------------------------------------------------
    # ATTENDANCE STATISTICS
    # ---------------------------------------------------------

    days_marked = records.count()

    days_present = records.filter(
        is_present=True
    ).count()

    days_absent = records.filter(
        is_present=False
    ).count()

    attendance_percentage = (
        round(
            (days_present / days_marked) * 100,
            1,
        )
        if days_marked
        else 0
    )

    return render(
        request,
        "attendance/student_history.html",
        {
            "student": student,
            "records": records,

            "current_term": current_term,

            "days_marked": days_marked,
            "days_present": days_present,
            "days_absent": days_absent,
            "attendance_percentage":
                attendance_percentage,
        },
    )