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

import datetime


def get_greeting():
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"

def build_dashboard(user):
    """
    Build the dashboard context based on the user's role.
    """

    context = {
        "greeting": get_greeting(),
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

            "pending_submission_count": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.DRAFT
            ).count(),

            "pending_review": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.SUBMITTED
            ),

            "pending_approval": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.REVIEWED
            ),

            "pending_publish": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.APPROVED
            ),

            "published_count": SubjectAllocation.objects.filter(
                status=SubjectAllocation.Status.PUBLISHED
            ).count(),

        })

    if student:

        context["my_student_id"] = student.id

        current_term = context["current_term"]
        if current_term:
            from billing.models import get_cumulative_balance
            fee_amount, total_paid, balance = get_cumulative_balance(student, current_term)
            context["my_fee_amount"] = fee_amount
            context["my_total_paid"] = total_paid
            context["my_balance"] = balance
            context["my_fee_term"] = current_term

    return context