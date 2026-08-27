from django.test import TestCase

# Create your tests here.
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School, SchoolRole, Permission


class SubjectPermissionTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            code="SUBJECT-TEST",
        )

        self.view_permission = Permission.objects.create(
            code="subjects.view",
            name="View Subjects",
            module="Subjects",
            description="View school subjects.",
            is_active=True,
        )

        self.manage_permission = Permission.objects.create(
            code="subjects.manage",
            name="Manage Subjects",
            module="Subjects",
            description="Create, edit and manage subjects.",
            is_active=True,
        )

        self.assign_permission = Permission.objects.create(
            code="subjects.assign",
            name="Assign Subjects",
            module="Subjects",
            description="Assign subjects to classes.",
            is_active=True,
        )

        self.role = SchoolRole.objects.create(
            school=self.school,
            name="Subject Manager",
        )

        self.user = User.objects.create_user(
            username="subjectuser",
            password="password123",
            school=self.school,
            role=User.Role.TEACHER,
            school_role=self.role,
        )

    def login(self):
        self.client.login(
            username="subjectuser",
            password="password123",
        )

    def test_subject_view_permission_allows_subject_list(self):
        self.role.permissions.add(
            self.view_permission
        )

        self.login()

        response = self.client.get(
            reverse("subject_list")
        )

        self.assertEqual(response.status_code, 200)

    def test_subject_view_permission_denies_without_permission(self):
        self.login()

        response = self.client.get(
            reverse("subject_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_subject_manage_permission_exists(self):
        self.role.permissions.add(
            self.manage_permission
        )

        self.assertTrue(
            self.role.permissions.filter(
                code="subjects.manage",
                is_active=True,
            ).exists()
        )

    def test_subject_assign_permission_exists(self):
        self.role.permissions.add(
            self.assign_permission
        )

        self.assertTrue(
            self.role.permissions.filter(
                code="subjects.assign",
                is_active=True,
            ).exists()
        )

    def test_permission_from_another_school_does_not_grant_access(self):
        other_school = School.objects.create(
            name="Other School",
            code="SUBJECT-OTHER",
        )

        other_role = SchoolRole.objects.create(
            school=other_school,
            name="Other School Manager",
        )

        other_role.permissions.add(
            self.view_permission
        )

        self.user.school_role = other_role
        self.user.save(
            update_fields=["school_role"]
        )

        self.login()

        response = self.client.get(
            reverse("subject_list")
        )

        self.assertEqual(response.status_code, 403)