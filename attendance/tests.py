from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School, SchoolRole, Permission
from students.models import SchoolClass
from teachers.models import Teacher


class AttendancePermissionTests(TestCase):

    def setUp(self):
        # --------------------------------------------------
        # SCHOOLS
        # --------------------------------------------------

        self.school1 = School.objects.create(
            name="School One",
            code="ATT001",
        )

        self.school2 = School.objects.create(
            name="School Two",
            code="ATT002",
        )

        # --------------------------------------------------
        # PERMISSIONS
        # --------------------------------------------------

        self.mark_permission = Permission.objects.create(
            code="attendance.mark",
            name="Mark Attendance",
            module="Attendance",
            description="Mark student attendance.",
        )

        self.view_permission = Permission.objects.create(
            code="attendance.view",
            name="View Attendance",
            module="Attendance",
            description="View attendance records and summaries.",
        )

        # --------------------------------------------------
        # SCHOOL ROLE
        # --------------------------------------------------

        self.role = SchoolRole.objects.create(
            school=self.school1,
            name="Attendance Manager",
        )

        # --------------------------------------------------
        # USER
        # --------------------------------------------------

        self.user = User.objects.create_user(
            username="attendanceuser",
            password="TestPassword123!",
            first_name="Attendance",
            last_name="User",
            school=self.school1,
            role=User.Role.ADMIN,
        )

        self.user.school_role = self.role
        self.user.save(
            update_fields=["school_role"]
        )

        # --------------------------------------------------
        # CLASS
        # --------------------------------------------------

        self.class1 = SchoolClass.objects.create(
            school=self.school1,
            name="Primary 1",
            section=SchoolClass.Section.PRIMARY,
        )

        self.class2 = SchoolClass.objects.create(
            school=self.school2,
            name="Primary 1",
            section=SchoolClass.Section.PRIMARY,
        )

    # ======================================================
    # HELPER
    # ======================================================

    def login(self):
        self.client.force_login(self.user)

    # ======================================================
    # ATTENDANCE.MARK
    # ======================================================

    def test_attendance_mark_permission_allows_class_selection(self):
        self.role.permissions.add(
            self.mark_permission
        )

        self.login()

        response = self.client.get(
            reverse("select_class_for_attendance")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_attendance_mark_permission_denies_class_selection_without_permission(self):
        self.login()

        response = self.client.get(
            reverse("select_class_for_attendance")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_attendance_mark_permission_allows_mark_attendance(self):
        self.role.permissions.add(
            self.mark_permission
        )

        self.login()

        response = self.client.get(
            reverse(
                "mark_attendance",
                kwargs={
                    "class_id": self.class1.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_attendance_mark_permission_denies_mark_attendance_without_permission(self):
        self.login()

        response = self.client.get(
            reverse(
                "mark_attendance",
                kwargs={
                    "class_id": self.class1.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ======================================================
    # ATTENDANCE.VIEW
    # ======================================================

    def test_attendance_view_permission_denies_summary_without_permission(self):
        self.login()

        response = self.client.get(
            reverse("class_attendance_summary")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ======================================================
    # SCHOOL ISOLATION
    # ======================================================

    def test_attendance_cannot_access_class_from_another_school(self):
        self.role.permissions.add(
            self.mark_permission
        )

        self.login()

        response = self.client.get(
            reverse(
                "mark_attendance",
                kwargs={
                    "class_id": self.class2.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )