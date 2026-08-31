from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School, SchoolRole
from .models import MaintenanceMode



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

        self.principal_role = SchoolRole.objects.create(
            school=self.school,
            name="Principal",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        self.principal = User.objects.create_user(
            username="principal",
            password=self.user_password,
            school=self.school,
            role=User.Role.ADMIN,
            school_role=self.principal_role,
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
        
    def test_platform_admin_can_enable_maintenance_mode(self):
        self.login("platformadmin")

        response = self.client.post(
            reverse("maintenance_home"),
            {
                "action": "enable",
                "message": "Paul SchoolHub is undergoing scheduled maintenance.",
            },
        )

        self.assertEqual(response.status_code, 302)

        maintenance = MaintenanceMode.get_solo()

        self.assertTrue(maintenance.is_enabled)
        self.assertEqual(
            maintenance.message,
            "Paul SchoolHub is undergoing scheduled maintenance.",
        )


    def test_platform_admin_can_disable_maintenance_mode(self):
        self.login("platformadmin")

        maintenance = MaintenanceMode.get_solo()
        maintenance.is_enabled = True
        maintenance.message = "Maintenance in progress."
        maintenance.save()

        response = self.client.post(
            reverse("maintenance_home"),
            {
                "action": "disable",
                "message": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        maintenance.refresh_from_db()

        self.assertFalse(maintenance.is_enabled)
        self.assertEqual(maintenance.message, "")
        

class MaintenanceModeTests(TestCase):

    def test_get_solo_creates_singleton(self):
        maintenance = MaintenanceMode.get_solo()

        self.assertEqual(MaintenanceMode.objects.count(), 1)
        self.assertEqual(maintenance.pk, 1)
        self.assertFalse(maintenance.is_enabled)

    def test_get_solo_returns_existing_singleton(self):
        first = MaintenanceMode.get_solo()
        second = MaintenanceMode.get_solo()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(MaintenanceMode.objects.count(), 1)

    def test_get_solo_maintains_singleton(self):
        maintenance = MaintenanceMode.get_solo()

        maintenance.is_enabled = True
        maintenance.message = "Scheduled maintenance"
        maintenance.save()

        same_maintenance = MaintenanceMode.get_solo()

        self.assertEqual(maintenance.pk, 1)
        self.assertEqual(same_maintenance.pk, 1)
        self.assertEqual(MaintenanceMode.objects.count(), 1)
        self.assertTrue(same_maintenance.is_enabled)
        self.assertEqual(
            same_maintenance.message,
            "Scheduled maintenance",
        )

    def test_maintenance_mode_can_be_enabled_and_disabled(self):
        maintenance = MaintenanceMode.get_solo()

        maintenance.is_enabled = True
        maintenance.message = "System maintenance in progress."
        maintenance.save()

        maintenance.refresh_from_db()

        self.assertTrue(maintenance.is_enabled)
        self.assertEqual(
            maintenance.message,
            "System maintenance in progress.",
        )

        maintenance.is_enabled = False
        maintenance.save()

        maintenance.refresh_from_db()

        self.assertFalse(maintenance.is_enabled)

    def test_maintenance_mode_cannot_be_deleted(self):
        maintenance = MaintenanceMode.get_solo()

        with self.assertRaises(ValueError):
            maintenance.delete()

        self.assertEqual(MaintenanceMode.objects.count(), 1)
    
    def test_public_user_can_access_maintenance_status_page(self):
        response = self.client.get(
            reverse("maintenance_status")
        )

        self.assertEqual(response.status_code, 200)


    def test_maintenance_status_page_uses_configured_message(self):
        maintenance = MaintenanceMode.get_solo()

        maintenance.message = (
            "Paul SchoolHub is undergoing scheduled maintenance."
        )

        maintenance.save()

        response = self.client.get(
            reverse("maintenance_status")
        )

        self.assertContains(
            response,
            "Paul SchoolHub is undergoing scheduled maintenance.",
        )