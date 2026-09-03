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

from django.test import TestCase
from django.urls import reverse
from django.core import mail

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




class TeacherRegistrationTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Registration Test School",
            code="REG-001",
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            start_date=timezone.now().date(),
        )

        self.permission = Permission.objects.create(
            code="teachers.add",
            name="Add Teachers",
            module="Teachers",
            description="Add teacher records.",
            is_active=True,
        )

        self.role = SchoolRole.objects.create(
            school=self.school,
            name="Teacher Manager",
        )

        self.role.permissions.add(self.permission)

        self.user = User.objects.create_user(
            username="manager",
            password="password123",
            first_name="Test",
            last_name="Manager",
            email="manager@example.com",
            school=self.school,
            role=User.Role.ADMIN,
            school_role=self.role,
        )

    def test_teacher_registration_creates_user_without_usable_password(self):
        self.client.login(
            username="manager",
            password="password123",
        )

        response = self.client.post(
            reverse("register_teacher"),
            {
                "username": "newteacher",
                "first_name": "New",
                "last_name": "Teacher",
                "email": "teacher@example.com",
                "years_of_experience": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        teacher_user = User.objects.get(
            username="newteacher"
        )

        teacher = Teacher.objects.get(
            user=teacher_user
        )

        self.assertFalse(
            teacher_user.has_usable_password()
        )

        self.assertEqual(
            teacher_user.school,
            self.school,
        )

        self.assertEqual(
            teacher.school,
            self.school,
        )

        self.assertTrue(
            teacher.staff_id.startswith("REG-001-STF-")
        )

    def test_teacher_registration_sends_password_setup_link(self):
        self.client.login(
            username="manager",
            password="password123",
        )

        response = self.client.post(
            reverse("register_teacher"),
            {
                "username": "emailedteacher",
                "first_name": "Emailed",
                "last_name": "Teacher",
                "email": "emailed@example.com",
                "years_of_experience": 3,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["emailed@example.com"],
        )

        self.assertEqual(
            email.subject,
            "Set Up Your Paul SchoolHub Password",
        )

        self.assertIn(
            "Set your password using this link:",
            email.body,
        )

        self.assertIn(
            "/set-password/",
            email.body,
        )

        self.assertNotIn(
            "password123",
            email.body,
        )