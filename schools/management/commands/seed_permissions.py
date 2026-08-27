from django.core.management.base import BaseCommand

from schools.models import Permission


PERMISSIONS = [

    # =========================================================
    # STUDENTS
    # =========================================================

    {
        "code": "students.view",
        "name": "View Students",
        "module": "Students",
        "description": "View student records.",
    },
    {
        "code": "students.add",
        "name": "Add Students",
        "module": "Students",
        "description": "Create new student records.",
    },
    {
        "code": "students.change",
        "name": "Edit Students",
        "module": "Students",
        "description": "Edit student records.",
    },
    {
        "code": "students.delete",
        "name": "Delete Students",
        "module": "Students",
        "description": "Delete student records.",
    },

    # =========================================================
    # TEACHERS
    # =========================================================

    {
        "code": "teachers.view",
        "name": "View Teachers",
        "module": "Teachers",
        "description": "View teacher records.",
    },
    {
        "code": "teachers.add",
        "name": "Add Teachers",
        "module": "Teachers",
        "description": "Create teacher records.",
    },
    {
        "code": "teachers.change",
        "name": "Edit Teachers",
        "module": "Teachers",
        "description": "Edit teacher records.",
    },
    {
        "code": "teachers.delete",
        "name": "Delete Teachers",
        "module": "Teachers",
        "description": "Delete teacher records.",
    },

    # =========================================================
    # SUBJECTS
    # =========================================================

    {
        "code": "subjects.view",
        "name": "View Subjects",
        "module": "Subjects",
        "description": "View school subjects.",
    },
    {
        "code": "subjects.manage",
        "name": "Manage Subjects",
        "module": "Subjects",
        "description": "Create, edit and manage subjects.",
    },
    {
        "code": "subjects.assign",
        "name": "Assign Subjects",
        "module": "Subjects",
        "description": "Assign subjects to classes.",
    },

    # =========================================================
    # CLASSES
    # =========================================================

    {
        "code": "classes.view",
        "name": "View Classes",
        "module": "Classes",
        "description": "View school classes.",
    },
    {
        "code": "classes.manage",
        "name": "Manage Classes",
        "module": "Classes",
        "description": "Create and manage classes.",
    },
    {
        "code": "classes.promote",
        "name": "Promote Students",
        "module": "Classes",
        "description": "Promote students to another class.",
    },

    # =========================================================
    # SCORES / RESULTS
    # =========================================================

    {
        "code": "scores.view",
        "name": "View Scores",
        "module": "Scores",
        "description": "View student scores and results.",
    },
    {
        "code": "scores.enter",
        "name": "Enter Scores",
        "module": "Scores",
        "description": "Enter student continuous assessment and examination scores.",
    },
    {
        "code": "scores.change",
        "name": "Edit Scores",
        "module": "Scores",
        "description": "Edit previously entered student scores.",
    },
    {
        "code": "scores.submit",
        "name": "Submit Scores",
        "module": "Scores",
        "description": "Submit completed scores for review.",
    },
    {
        "code": "scores.review",
        "name": "Review Scores",
        "module": "Scores",
        "description": "Review submitted scores.",
    },
    {
        "code": "scores.approve",
        "name": "Approve Results",
        "module": "Scores",
        "description": "Approve reviewed results.",
    },
    {
        "code": "scores.publish",
        "name": "Publish Results",
        "module": "Scores",
        "description": "Publish approved results to students.",
    },

    # =========================================================
    # REPORT CARDS
    # =========================================================

    {
        "code": "reports.view",
        "name": "View Report Cards",
        "module": "Reports",
        "description": "View student report cards.",
    },
    {
        "code": "reports.teacher_remark",
        "name": "Edit Teacher Remark",
        "module": "Reports",
        "description": "Enter or edit teacher remarks.",
    },
    {
        "code": "reports.principal_remark",
        "name": "Edit Principal Remark",
        "module": "Reports",
        "description": "Enter or edit principal remarks.",
    },

    # =========================================================
    # ATTENDANCE
    # =========================================================

    {
        "code": "attendance.view",
        "name": "View Attendance",
        "module": "Attendance",
        "description": "View attendance records and summaries.",
    },
    {
        "code": "attendance.mark",
        "name": "Mark Attendance",
        "module": "Attendance",
        "description": "Mark student attendance.",
    },
    {
        "code": "attendance.manage",
        "name": "Manage Attendance",
        "module": "Attendance",
        "description": "Edit and manage attendance records.",
    },

    # =========================================================
    # BILLING
    # =========================================================

    {
        "code": "billing.view",
        "name": "View Billing",
        "module": "Billing",
        "description": "View school financial and billing information.",
    },
    {
        "code": "billing.manage",
        "name": "Manage Billing",
        "module": "Billing",
        "description": "Manage fee structures and billing settings.",
    },
    {
        "code": "billing.record_payment",
        "name": "Record Payments",
        "module": "Billing",
        "description": "Record student fee payments.",
    },
    {
        "code": "billing.edit_payment",
        "name": "Edit Payments",
        "module": "Billing",
        "description": "Edit payment records.",
    },
    {
        "code": "billing.delete_payment",
        "name": "Delete Payments",
        "module": "Billing",
        "description": "Delete payment records.",
    },
    {
        "code": "billing.view_reports",
        "name": "View Billing Reports",
        "module": "Billing",
        "description": "View financial and billing reports.",
    },

    # =========================================================
    # ANNOUNCEMENTS
    # =========================================================

    {
        "code": "announcements.view",
        "name": "View Announcements",
        "module": "Announcements",
        "description": "View school announcements.",
    },
    {
        "code": "announcements.create",
        "name": "Create Announcements",
        "module": "Announcements",
        "description": "Create school announcements.",
    },
    {
        "code": "announcements.change",
        "name": "Edit Announcements",
        "module": "Announcements",
        "description": "Edit school announcements.",
    },
    {
        "code": "announcements.delete",
        "name": "Delete Announcements",
        "module": "Announcements",
        "description": "Delete school announcements.",
    },

    # =========================================================
    # ACADEMIC SESSION / TERMS
    # =========================================================

    {
        "code": "academics.view",
        "name": "View Academic Sessions",
        "module": "Academics",
        "description": "View academic sessions and terms.",
    },
    {
        "code": "academics.manage",
        "name": "Manage Academic Sessions",
        "module": "Academics",
        "description": "Create and manage academic sessions and terms.",
    },

    # =========================================================
    # SCHOOL SETTINGS
    # =========================================================

    {
        "code": "school_settings.view",
        "name": "View School Settings",
        "module": "School Settings",
        "description": "View school configuration and settings.",
    },
    {
        "code": "school_settings.manage",
        "name": "Manage School Settings",
        "module": "School Settings",
        "description": "Change school configuration and settings.",
    },

    # =========================================================
    # USERS / STAFF
    # =========================================================

    {
        "code": "users.view",
        "name": "View Users",
        "module": "Users",
        "description": "View school user accounts.",
    },
    {
        "code": "users.manage",
        "name": "Manage Users",
        "module": "Users",
        "description": "Create and manage school user accounts.",
    },

    # =========================================================
    # CLASS TEACHER FUNCTIONS
    # =========================================================

    {
        "code": "class_management.view",
        "name": "View Class Management",
        "module": "Class Management",
        "description": "View class management information.",
    },
    {
        "code": "class_management.manage",
        "name": "Manage Class Management",
        "module": "Class Management",
        "description": "Manage class assignments and related information.",
    },
]


class Command(BaseCommand):

    help = "Create or update the standard Paul SchoolHub permissions."

    def handle(self, *args, **options):

        created_count = 0
        updated_count = 0

        for permission_data in PERMISSIONS:

            permission, created = Permission.objects.update_or_create(
                code=permission_data["code"],
                defaults={
                    "name": permission_data["name"],
                    "module": permission_data["module"],
                    "description": permission_data["description"],
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Permission catalogue completed. "
                f"Created: {created_count}, "
                f"Updated: {updated_count}."
            )
        )