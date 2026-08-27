from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School, SchoolRole, Permission


class StudentPermissionTests(TestCase):

    def setUp(self):
        # -----------------------------------------------------
        # SCHOOLS
        # -----------------------------------------------------

        self.school_a = School.objects.create(
            name="School A",
            code="SCHA",
        )

        self.school_b = School.objects.create(
            name="School B",
            code="SCHB",
        )

        # -----------------------------------------------------
        # PERMISSIONS
        # -----------------------------------------------------

        self.students_view = Permission.objects.create(
            code="students.view",
            name="View Students",
            module="Students",
        )

        self.students_add = Permission.objects.create(
            code="students.add",
            name="Add Students",
            module="Students",
        )

        self.students_change = Permission.objects.create(
            code="students.change",
            name="Edit Students",
            module="Students",
        )

        self.classes_view = Permission.objects.create(
            code="classes.view",
            name="View Classes",
            module="Classes",
        )

        self.classes_manage = Permission.objects.create(
            code="classes.manage",
            name="Manage Classes",
            module="Classes",
        )

        self.classes_promote = Permission.objects.create(
            code="classes.promote",
            name="Promote Students",
            module="Classes",
        )

        # -----------------------------------------------------
        # SCHOOL ROLES
        # -----------------------------------------------------

        self.role_a = SchoolRole.objects.create(
            school=self.school_a,
            name="Test Role A",
        )

        self.role_b = SchoolRole.objects.create(
            school=self.school_b,
            name="Test Role B",
        )

        # -----------------------------------------------------
        # USERS
        # -----------------------------------------------------

        self.user_a = User.objects.create_user(
            username="school_a_user",
            password="testpassword123",
            school=self.school_a,
            role=User.Role.TEACHER,
            school_role=self.role_a,
        )

        self.user_b = User.objects.create_user(
            username="school_b_user",
            password="testpassword123",
            school=self.school_b,
            role=User.Role.TEACHER,
            school_role=self.role_b,
        )

    # =========================================================
    # STUDENTS
    # =========================================================

    def test_user_with_students_view_can_access_student_list(self):
        self.role_a.permissions.add(self.students_view)

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("student_list")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_students_view_cannot_access_student_list(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("student_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_user_with_students_add_can_access_registration(self):
        self.role_a.permissions.add(self.students_add)

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("register_student")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_students_add_cannot_access_registration(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("register_student")
        )

        self.assertEqual(response.status_code, 403)

    # =========================================================
    # CLASSES
    # =========================================================

    def test_user_with_classes_view_can_access_class_management(self):
        self.role_a.permissions.add(self.classes_view)

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("class_management")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_classes_view_cannot_access_class_management(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("class_management")
        )

        self.assertEqual(response.status_code, 403)

    def test_user_with_classes_manage_can_access_add_class(self):
        self.role_a.permissions.add(self.classes_manage)

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("add_class")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_classes_manage_cannot_access_add_class(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("add_class")
        )

        self.assertEqual(response.status_code, 403)

    def test_user_with_classes_promote_can_access_promote_class(self):
        self.role_a.permissions.add(self.classes_promote)

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("promote_class")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_classes_promote_cannot_access_promote_class(self):
        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("promote_class")
        )

        self.assertEqual(response.status_code, 403)

    # =========================================================
    # SCHOOL ISOLATION
    # =========================================================

    def test_school_a_permission_does_not_work_for_school_b(self):
        """
        A permission assigned to School A's role must not
        automatically give access to a School B user.
        """

        self.role_a.permissions.add(self.students_view)

        self.client.force_login(self.user_b)

        response = self.client.get(
            reverse("student_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_role_from_another_school_cannot_authorize_user(self):
        """
        Even if a user from School A is manually assigned
        a School B role, user_has_permission() must reject it.
        """

        self.role_b.permissions.add(self.students_view)

        self.user_a.school_role = self.role_b
        self.user_a.save(update_fields=["school_role"])

        self.client.force_login(self.user_a)

        response = self.client.get(
            reverse("student_list")
        )

        self.assertEqual(response.status_code, 403)