from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School


class MaintenancePermissionTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Maintenance Test School",
            code="MAINT-TEST",
        )

        self.user_password = "password123"

        self.platform_admin = User.objects.create_user(
            username="platformadmin",
            password=self.user_password,
            role=User.Role.PLATFORM_ADMIN,
        )

        self.school_admin = User.objects.create_user(
            username="schooladmin",
            password=self.user_password,
            school=self.school,
            role=User.Role.ADMIN,
        )

        self.principal = User.objects.create_user(
            username="principal",
            password=self.user_password,
            school=self.school,
            role=User.Role.PRINCIPAL,
        )

        self.teacher = User.objects.create_user(
            username="teacher",
            password=self.user_password,
            school=self.school,
            role=User.Role.TEACHER,
        )

        self.student = User.objects.create_user(
            username="student",
            password=self.user_password,
            school=self.school,
            role=User.Role.STUDENT,
        )

    def login(self, username):
        self.client.login(
            username=username,
            password=self.user_password,
        )

    def test_platform_admin_can_access_maintenance_home(self):
        self.login("platformadmin")

        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertEqual(response.status_code, 200)

    def test_platform_admin_can_access_backup_list(self):
        self.login("platformadmin")

        response = self.client.get(
            reverse("backup_list")
        )

        self.assertEqual(response.status_code, 200)

    def test_school_admin_cannot_access_maintenance(self):
        self.login("schooladmin")

        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertEqual(response.status_code, 403)

    def test_principal_cannot_access_maintenance(self):
        self.login("principal")

        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_cannot_access_maintenance(self):
        self.login("teacher")

        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_maintenance(self):
        self.login("student")

        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_access_maintenance(self):
        response = self.client.get(
            reverse("maintenance_home")
        )

        self.assertNotEqual(response.status_code, 200)