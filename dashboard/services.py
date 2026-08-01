from students.models import Student, SchoolClass
from teachers.models import Teacher
from subjects.models import Subject
from allocations.models import SubjectAllocation

from accounts.utils import (
    get_teacher,
    get_student,
    get_current_term,
    is_management_user,
)


def build_dashboard(user):
    """
    Build the dashboard context based on the user's role.
    """

    context = {
        "student_count": Student.objects.filter(is_active=True).count(),
        "teacher_count": Teacher.objects.filter(is_active=True).count(),
        "subject_count": Subject.objects.filter(is_active=True).count(),
        "class_count": SchoolClass.objects.count(),
        "allocation_count": SubjectAllocation.objects.count(),
        "current_term": get_current_term(),
        "is_admin_or_principal": is_management_user(user),
    }

    teacher = get_teacher(user)
    student = get_student(user)

    if teacher:
        allocations = SubjectAllocation.objects.filter(teacher=teacher)

        context.update({
            "my_allocations": allocations,
            "my_draft_count": allocations.filter(
                status=SubjectAllocation.Status.DRAFT
            ).count(),
        })

        if teacher.is_class_teacher and teacher.assigned_class:

            context.update({
                "pending_review": SubjectAllocation.objects.filter(
                    school_class=teacher.assigned_class,
                    status=SubjectAllocation.Status.SUBMITTED,
                ),

                "my_class_students": Student.objects.filter(
                    school_class=teacher.assigned_class,
                    is_active=True,
                ),

                "my_class_term": context["current_term"],
            })

    if context["is_admin_or_principal"]:

        context.update({

            "pending_approval": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.REVIEWED
            ),

            "pending_publish": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.APPROVED
            ),

        })

    if student:

        context["my_student_id"] = student.id

    return context