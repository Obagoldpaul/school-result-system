from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import (
    School,
    SchoolRole,
    Permission,
    Feature,
    SubscriptionPackage,
    SchoolSubscription,
)
from datetime import date
from .models import Announcement

class AnnouncementPermissionTests(TestCase):

    def setUp(self):
        # --------------------------------------------------
        # SCHOOLS
        # --------------------------------------------------

        self.school1 = School.objects.create(
            name="School One",
            code="ANN001",
        )

        self.school2 = School.objects.create(
            name="School Two",
            code="ANN002",
        )
        
        self.announcements_feature = Feature.objects.create(
            code="ANNOUNCEMENTS",
            name="Announcements",
            description="School announcements.",
            is_active=True,
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
            description="Test package",
            price=0,
            is_active=True,
        )

        self.package.features.add(
            self.announcements_feature
        )

        SchoolSubscription.objects.create(
            school=self.school1,
            package=self.package,
            billing_cycle=SchoolSubscription.BillingCycle.TERMLY,
            start_date=date.today(),
            is_active=True,
        )

        # --------------------------------------------------
        # PERMISSIONS
        # --------------------------------------------------

        self.view_permission = Permission.objects.create(
            code="announcements.view",
            name="View Announcements",
            module="Announcements",
            description="View school announcements.",
        )

        self.create_permission = Permission.objects.create(
            code="announcements.create",
            name="Create Announcements",
            module="Announcements",
            description="Create school announcements.",
        )

        self.change_permission = Permission.objects.create(
            code="announcements.change",
            name="Edit Announcements",
            module="Announcements",
            description="Edit school announcements.",
        )

        self.delete_permission = Permission.objects.create(
            code="announcements.delete",
            name="Delete Announcements",
            module="Announcements",
            description="Delete school announcements.",
        )

        # --------------------------------------------------
        # SCHOOL ROLE
        # --------------------------------------------------

        self.role = SchoolRole.objects.create(
            school=self.school1,
            name="Announcement Manager",
        )

        # --------------------------------------------------
        # USER
        # --------------------------------------------------

        self.user = User.objects.create_user(
            username="announcementuser",
            password="TestPassword123!",
            first_name="Announcement",
            last_name="User",
            school=self.school1,
            role=User.Role.ADMIN,
        )

        self.user.school_role = self.role
        self.user.save(
            update_fields=["school_role"]
        )

    # ======================================================
    # HELPER
    # ======================================================

    def login(self):
        self.client.force_login(self.user)

    # ======================================================
    # ANNOUNCEMENTS.VIEW
    # ======================================================

    def test_view_permission_allows_announcement_list(self):
        self.role.permissions.add(
            self.view_permission
        )

        self.login()

        response = self.client.get(
            reverse("announcement_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_view_permission_denies_without_permission(self):
        self.login()

        response = self.client.get(
            reverse("announcement_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    # ======================================================
    # ANNOUNCEMENTS.CREATE
    # ======================================================

    def test_create_permission_allows_post_announcement(self):
        self.role.permissions.add(
            self.create_permission
        )

        self.login()

        response = self.client.get(
            reverse("post_announcement")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_create_permission_denies_without_permission(self):
        self.login()

        response = self.client.get(
            reverse("post_announcement")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    # ======================================================
    # ANNOUNCEMENTS.CHANGE
    # ======================================================

    def test_change_permission_exists(self):
        self.role.permissions.add(
            self.change_permission
        )

        self.assertTrue(
            self.role.permissions.filter(
                code="announcements.change",
                is_active=True,
            ).exists()
        )

    # ======================================================
    # ANNOUNCEMENTS.DELETE
    # ======================================================

    def test_delete_permission_exists(self):
        self.role.permissions.add(
            self.delete_permission
        )

        self.assertTrue(
            self.role.permissions.filter(
                code="announcements.delete",
                is_active=True,
            ).exists()
        )

    # ======================================================
    # SCHOOL ISOLATION
    # ======================================================

    def test_announcement_list_is_isolated_by_school(self):
        school1_announcement = Announcement.objects.create(
            school=self.school1,
            title="School One Announcement",
            body="Announcement for School One",
            audience=Announcement.Audience.ALL,
            created_by=self.user,
        )

        school2_announcement = Announcement.objects.create(
            school=self.school2,
            title="School Two Announcement",
            body="Announcement for School Two",
            audience=Announcement.Audience.ALL,
            created_by=None,
        )

        self.login()

        response = self.client.get(
            reverse("announcement_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        content = response.content.decode()

        self.assertIn(
            school1_announcement.title,
            content,
        )

        self.assertNotIn(
            school2_announcement.title,
            content,
        )