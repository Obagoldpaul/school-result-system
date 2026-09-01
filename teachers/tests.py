from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import (
    School,
    SchoolRole,
    Permission,
    SubscriptionPackage,
    SchoolSubscription,
)
from django.utils import timezone
from teachers.models import Teacher


class TeacherPermissionTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            code="TEST-001",
        )
        
        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            start_date=timezone.now().date(),
        )

        self.view_permission = Permission.objects.create(
            code="teachers.view",
            name="View Teachers",
            module="Teachers",
            description="View teacher records.",
            is_active=True,
        )

        self.change_permission = Permission.objects.create(
            code="teachers.change",
            name="Edit Teachers",
            module="Teachers",
            description="Edit teacher records.",
            is_active=True,
        )

        self.view_role = SchoolRole.objects.create(
            school=self.school,
            name="Teacher Viewer",
        )

        self.change_role = SchoolRole.objects.create(
            school=self.school,
            name="Teacher Manager",
        )

        self.view_role.permissions.add(
            self.view_permission
        )

        self.change_role.permissions.add(
            self.change_permission
        )

        self.user = User.objects.create_user(
            username="teacher_viewer",
            password="password123",
            school=self.school,
            role=User.Role.TEACHER,
            school_role=self.view_role,
        )

    def test_user_with_teachers_view_can_access_teacher_list(self):
        self.client.login(
            username="teacher_viewer",
            password="password123",
        )

        response = self.client.get(
            reverse("teacher_list")
        )

        self.assertEqual(response.status_code, 200)

    def test_user_without_teachers_view_is_denied(self):
        self.user.school_role.permissions.clear()

        self.client.login(
            username="teacher_viewer",
            password="password123",
        )

        response = self.client.get(
            reverse("teacher_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_user_with_teachers_change_has_change_permission(self):
        self.assertTrue(
            self.change_role.permissions.filter(
                code="teachers.change"
            ).exists()
        )