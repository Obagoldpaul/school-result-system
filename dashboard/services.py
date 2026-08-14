from students.models import Student, SchoolClass
from teachers.models import Teacher
from subjects.models import Subject
from allocations.models import SubjectAllocation
from accounts.permissions import can_manage_billing

from billing.models import Payment, get_cumulative_balance
from django.db.models import Sum

from accounts.utils import (
    get_teacher,
    get_student,
    get_current_term,
    is_management_user,
)

from students.birthday_utils import (
    get_today_birthdays,
    get_upcoming_birthdays,
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

    All dashboard data is restricted to the logged-in
    user's school to maintain multi-tenant data isolation.
    """

    school = user.school

    context = {
        "greeting": get_greeting(),

        # --------------------------------------------------
        # SCHOOL STATISTICS
        # --------------------------------------------------

        "student_count": Student.objects.filter(
            user__school=school,
            is_active=True,
        ).count(),

        "teacher_count": Teacher.objects.filter(
            user__school=school,
            is_active=True,
        ).count(),

        "subject_count": Subject.objects.filter(
            school=school,
            is_active=True,
        ).count(),

        "class_count": SchoolClass.objects.filter(
            school=school,
        ).count(),

        "allocation_count": SubjectAllocation.objects.filter(
            school_class__school=school,
        ).count(),

        # --------------------------------------------------
        # ACADEMIC INFORMATION
        # --------------------------------------------------

        "current_term": get_current_term(user),

        # --------------------------------------------------
        # PERMISSIONS
        # --------------------------------------------------

        "is_management": is_management_user(user),

        "can_manage_billing": can_manage_billing(user),

        # --------------------------------------------------
        # BIRTHDAYS
        # Management will use these on the dashboard.
        # --------------------------------------------------

        "today_birthdays": [],

        "upcoming_birthdays": [],
    }

    teacher = get_teacher(user)
    student = get_student(user)

    # ======================================================
    # BIRTHDAYS
    # ======================================================

    if context["is_management"] and school:

        context["today_birthdays"] = get_today_birthdays(
            school
        )

        context["upcoming_birthdays"] = get_upcoming_birthdays(
            school,
            days=30,
        )

    # ======================================================
    # BURSAR / BILLING DASHBOARD
    # ======================================================

    if can_manage_billing(user):

        billing_term = context["current_term"]

        billing_context = {
            "billing_total_collected": 0,
            "billing_students_owing": 0,
            "billing_outstanding": 0,
            "billing_expected_revenue": 0,
            "billing_collection_rate": 0,
            "billing_recent_payments": [],
        }

        if billing_term and school:

            # Only students belonging to this school.
            students = Student.objects.filter(
                user__school=school,
                is_active=True,
            )

            # Only payments belonging to students in this school.
            total_collected = Payment.objects.filter(
                student__user__school=school,
                term=billing_term,
            ).aggregate(
                total=Sum("amount")
            )["total"] or 0

            students_owing = 0
            outstanding = 0

            for s in students:

                fee_amount, total_paid, balance = (
                    get_cumulative_balance(
                        s,
                        billing_term
                    )
                )

                if balance > 0:
                    students_owing += 1
                    outstanding += balance

            expected_revenue = (
                total_collected + outstanding
            )

            collection_rate = 0

            if expected_revenue > 0:

                collection_rate = (
                    total_collected
                    / expected_revenue
                ) * 100

            # Only show payments from this school.
            recent_payments = (
                Payment.objects
                .select_related(
                    "student",
                    "student__user",
                    "term",
                )
                .filter(
                    student__user__school=school,
                    term=billing_term,
                )
                .order_by(
                    "-date_paid",
                    "-id",
                )[:5]
            )

            billing_context.update({

                "billing_total_collected":
                    total_collected,

                "billing_students_owing":
                    students_owing,

                "billing_outstanding":
                    outstanding,

                "billing_expected_revenue":
                    expected_revenue,

                "billing_collection_rate":
                    round(
                        collection_rate,
                        2
                    ),

                "billing_recent_payments":
                    recent_payments,
            })

        context.update(
            billing_context
        )

    # ======================================================
    # TEACHER DASHBOARD
    # ======================================================

    if teacher:

        allocations = (
            SubjectAllocation.objects
            .filter(
                school_class__school=school,
                teacher=teacher,
            )
        )

        context.update({

            "my_allocations":
                allocations,

            "my_draft_count":
                allocations.filter(
                    status=SubjectAllocation.Status.DRAFT
                ).count(),

            "my_submitted_count":
                allocations.filter(
                    status=SubjectAllocation.Status.SUBMITTED
                ).count(),

            "my_approved_count":
                allocations.filter(
                    status=SubjectAllocation.Status.APPROVED
                ).count(),
        })

        # --------------------------------------------------
        # CLASS TEACHER
        # --------------------------------------------------

        if (
            teacher.is_class_teacher
            and teacher.assigned_class
        ):

            class_allocations = (
                SubjectAllocation.objects
                .filter(
                    school_class=teacher.assigned_class,
                    school_class__school=school,
                )
            )

            my_class_students = (
                Student.objects
                .filter(
                    school_class=teacher.assigned_class,
                    user__school=school,
                    is_active=True,
                )
            )

            context.update({

                "pending_review":
                    class_allocations.filter(
                        status=SubjectAllocation.Status.SUBMITTED,
                    ),

                "completed_review_count":
                    class_allocations.exclude(
                        status__in=[
                            SubjectAllocation.Status.DRAFT,
                            SubjectAllocation.Status.SUBMITTED,
                        ]
                    ).count(),

                "my_class_students":
                    my_class_students,

                "my_class_term":
                    context["current_term"],
            })

            # --------------------------------------------------
            # PENDING TEACHER REMARKS
            # --------------------------------------------------

            if context["current_term"]:

                from scores.models import ReportCardExtra

                pending_remarks = 0

                for s in my_class_students:

                    extra = (
                        ReportCardExtra.objects
                        .filter(
                            student=s,
                            term=context["current_term"],
                        )
                        .first()
                    )

                    if (
                        not extra
                        or not extra.teacher_remark
                    ):
                        pending_remarks += 1

                context[
                    "pending_remarks_count"
                ] = pending_remarks

    # ======================================================
    # MANAGEMENT DASHBOARD
    # ======================================================

    if context["is_management"] and school:

        # --------------------------------------------------
        # SUBJECT ALLOCATION WORKFLOW
        # --------------------------------------------------

        context.update({

            "pending_submission_count":
                SubjectAllocation.objects.filter(
                    school_class__school=school,
                    status=SubjectAllocation.Status.DRAFT,
                ).count(),

            "pending_review":
                SubjectAllocation.objects.filter(
                    school_class__school=school,
                    status=SubjectAllocation.Status.SUBMITTED,
                ),

            "pending_approval":
                SubjectAllocation.objects.filter(
                    school_class__school=school,
                    status=SubjectAllocation.Status.REVIEWED,
                ),

            "pending_publish":
                SubjectAllocation.objects.filter(
                    school_class__school=school,
                    status=SubjectAllocation.Status.APPROVED,
                ),

            "published_count":
                SubjectAllocation.objects.filter(
                    school_class__school=school,
                    status=SubjectAllocation.Status.PUBLISHED,
                ).count(),
        })

        # --------------------------------------------------
        # RECENT ACTIVITIES
        # --------------------------------------------------

        from activitylog.models import ActivityLog

        context["recent_activities"] = (
            ActivityLog.objects
            .filter(
                user__school=school
            )
            .select_related(
                "user"
            )[:10]
        )

    # ======================================================
    # STUDENT DASHBOARD
    # ======================================================

    if student:

        context["my_student_id"] = student.id

        # --------------------------------------------------
        # SUBJECT REGISTRATION
        # --------------------------------------------------

        from subjects.models import ClassSubject

        registered_count = (
            ClassSubject.objects
            .filter(
                school_class=student.school_class,
                school_class__school=school,
            )
            .count()
        )

        elective_count = (
            student.elective_subjects.count()
        )

        context["subjects_registered"] = (
            registered_count + elective_count
        )

        # --------------------------------------------------
        # BILLING
        # --------------------------------------------------

        current_term = context["current_term"]

        if current_term:

            (
                fee_amount,
                total_paid,
                balance,
            ) = get_cumulative_balance(
                student,
                current_term
            )

            context["my_fee_amount"] = (
                fee_amount
            )

            context["my_total_paid"] = (
                total_paid
            )

            context["my_balance"] = (
                balance
            )

            context["my_fee_term"] = (
                current_term
            )

            # --------------------------------------------------
            # RESULT PUBLICATION
            # --------------------------------------------------

            from scores.models import (
                is_class_term_fully_published
            )

            context[
                "latest_result_published"
            ] = is_class_term_fully_published(
                student.school_class,
                current_term,
            )

    return context