from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.test import TestCase

from schools.views import setup_new_school
from students.models import SchoolClass

from schools.models import (
    School,
    SchoolRole,
    SubscriptionPackage,
    SchoolSubscription,
)


class SchoolProvisioningTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions")

    def test_primary_secondary_school_gets_default_provisioning(self):
        school = School.objects.create(
            name="Provisioning Test School",
            code="PROVTEST",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
            email="provisioning-test@example.com",
            phone="0000000000",
            address="Temporary Test School",
        )

        setup_new_school(school)

        self.assertEqual(
            SchoolClass.objects.filter(school=school).count(),
            15,
        )
        
        self.assertFalse(
            SchoolClass.objects.filter(
                school=school,
                name="BASIC 6",
            ).exists()
        )

        self.assertEqual(
            SchoolRole.objects.filter(school=school).count(),
            4,
        )

        expected_permissions = {
            "Principal": 46,
            "Bursar": 6,
            "Class Teacher": 17,
            "Teacher": 11,
        }

        for role_name, expected_count in expected_permissions.items():
            role = SchoolRole.objects.get(
                school=school,
                name=role_name,
            )

            self.assertEqual(
                role.permissions.filter(is_active=True).count(),
                expected_count,
                msg=f"{role_name} permission count is incorrect.",
            )

    def test_setup_new_school_is_idempotent(self):
        school = School.objects.create(
            name="Idempotency Test School",
            code="IDEMPTEST",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
            email="idempotency-test@example.com",
            phone="0000000000",
            address="Temporary Test School",
        )

        setup_new_school(school)

        first_class_count = SchoolClass.objects.filter(
            school=school
        ).count()

        first_role_count = SchoolRole.objects.filter(
            school=school
        ).count()

        setup_new_school(school)

        second_class_count = SchoolClass.objects.filter(
            school=school
        ).count()

        second_role_count = SchoolRole.objects.filter(
            school=school
        ).count()

        self.assertEqual(first_class_count, 15)
        self.assertEqual(first_role_count, 4)
        self.assertEqual(second_class_count, first_class_count)
        self.assertEqual(second_role_count, first_role_count)


class SendUserSetupLinkTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions")

        cls.school = School.objects.create(
            name="Setup Link Test School",
            code="SETUPTEST",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
            email="school@example.com",
            phone="0000000000",
            address="Temporary Test School",
        )

        cls.other_school = School.objects.create(
            name="Other Test School",
            code="OTHERTEST",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
            email="other@example.com",
            phone="0000000000",
            address="Temporary Other School",
        )

        User = get_user_model()

        cls.platform_admin = User.objects.create_user(
            username="setup_platform_admin",
            email="admin@example.com",
            password="AdminPassword123!",
            role=User.Role.PLATFORM_ADMIN,
        )

        cls.pending_user = User.objects.create(
            username="pending_setup_user",
            first_name="Pending",
            last_name="User",
            email="pending@example.com",
            role=User.Role.TEACHER,
            school=cls.school,
        )
        cls.pending_user.set_unusable_password()
        cls.pending_user.save()

        cls.password_user = User.objects.create_user(
            username="existing_password_user",
            first_name="Existing",
            last_name="Password",
            email="existing@example.com",
            password="ExistingPassword123!",
            role=User.Role.TEACHER,
            school=cls.school,
        )

        cls.no_email_user = User.objects.create(
            username="no_email_user",
            first_name="No",
            last_name="Email",
            email="",
            role=User.Role.TEACHER,
            school=cls.school,
        )
        cls.no_email_user.set_unusable_password()
        cls.no_email_user.save()

        cls.other_school_user = User.objects.create(
            username="other_school_user",
            first_name="Other",
            last_name="School",
            email="other-user@example.com",
            role=User.Role.TEACHER,
            school=cls.other_school,
        )
        cls.other_school_user.set_unusable_password()
        cls.other_school_user.save()
        
    def test_pending_user_with_email_receives_setup_link(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse(
                "send_user_setup_link",
                kwargs={
                    "school_id": self.school.id,
                    "user_id": self.pending_user.id,
                },
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "school_users",
                kwargs={"school_id": self.school.id},
            ),
        )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["pending@example.com"],
        )

        self.assertIn(
            "Set Up Your Paul SchoolHub Password",
            email.subject,
        )

        self.assertIn(
            "/set-password/",
            email.body,
        )

        self.assertIn(
            self.school.name,
            email.body,
        )
        
    def test_user_with_existing_password_is_rejected(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse(
                "send_user_setup_link",
                kwargs={
                    "school_id": self.school.id,
                    "user_id": self.password_user.id,
                },
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "school_users",
                kwargs={"school_id": self.school.id},
            ),
        )

        self.assertEqual(len(mail.outbox), 0)
        
    def test_user_without_email_is_rejected(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse(
                "send_user_setup_link",
                kwargs={
                    "school_id": self.school.id,
                    "user_id": self.no_email_user.id,
                },
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "school_users",
                kwargs={"school_id": self.school.id},
            ),
        )

        self.assertEqual(len(mail.outbox), 0)
    
    def test_user_from_another_school_cannot_be_targeted(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse(
                "send_user_setup_link",
                kwargs={
                    "school_id": self.school.id,
                    "user_id": self.other_school_user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)
        
    def test_get_request_is_not_allowed(self):
        self.client.force_login(self.platform_admin)

        response = self.client.get(
            reverse(
                "send_user_setup_link",
                kwargs={
                    "school_id": self.school.id,
                    "user_id": self.pending_user.id,
                },
            )
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(len(mail.outbox), 0)
        

class CreateSchoolUserTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions")

        cls.school = School.objects.create(
            name="Create User Test School",
            code="CREATEUSER",
            school_type=School.SchoolType.PRIMARY_SECONDARY,
            email="school@example.com",
            phone="0000000000",
            address="Temporary Test School",
        )

        User = get_user_model()

        cls.platform_admin = User.objects.create_user(
            username="create_user_platform_admin",
            email="admin@example.com",
            password="AdminPassword123!",
            role=User.Role.PLATFORM_ADMIN,
        )

    def test_create_school_user_sends_setup_link(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse(
                "create_school_user",
                kwargs={"school_id": self.school.id},
            ),
            {
                "username": "new_school_admin",
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "school_users",
                kwargs={"school_id": self.school.id},
            ),
        )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["newadmin@example.com"],
        )

        self.assertIn(
            "Set Up Your Paul SchoolHub Password",
            email.subject,
        )

        self.assertIn(
            "/set-password/",
            email.body,
        )

        self.assertIn(
            self.school.name,
            email.body,
        )

        user = get_user_model().objects.get(
            username="new_school_admin"
        )

        self.assertEqual(
            user.school,
            self.school,
        )

        self.assertEqual(
            user.role,
            get_user_model().Role.ADMIN,
        )

        self.assertFalse(
            user.has_usable_password()
        )

class CreateSchoolTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions")

        cls.platform_admin = get_user_model().objects.create_user(
            username="create_school_platform_admin",
            email="platform@example.com",
            password="AdminPassword123!",
            role=get_user_model().Role.PLATFORM_ADMIN,
        )

        cls.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
            price=10000,
            is_active=True,
        )

    def test_create_school_sends_first_admin_setup_link(self):
        self.client.force_login(self.platform_admin)

        response = self.client.post(
            reverse("create_school"),
            {
                "school_name": "New Test College",
                "school_code": "NEWCOLLEGE",
                "school_type": School.SchoolType.PRIMARY_SECONDARY,
                "email": "school@example.com",
                "phone": "0000000000",
                "address": "Temporary Test School",
                "package": self.package.id,
                "billing_cycle": SchoolSubscription.BillingCycle.YEARLY,
                "admin_first_name": "First",
                "admin_last_name": "Administrator",
                "admin_username": "first_school_admin",
                "admin_email": "firstadmin@example.com",
            },
        )

        self.assertRedirects(
            response,
            reverse("platform_dashboard"),
        )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["firstadmin@example.com"],
        )

        self.assertIn(
            "Set Up Your Paul SchoolHub Password",
            email.subject,
        )

        self.assertIn(
            "/set-password/",
            email.body,
        )

        school = School.objects.get(
            code="NEWCOLLEGE"
        )

        self.assertIn(
            school.name,
            email.body,
        )

        administrator = get_user_model().objects.get(
            username="first_school_admin"
        )

        self.assertEqual(
            administrator.school,
            school,
        )

        self.assertEqual(
            administrator.role,
            get_user_model().Role.ADMIN,
        )

        self.assertFalse(
            administrator.has_usable_password()
        )

        subscription = SchoolSubscription.objects.get(
            school=school
        )

        self.assertEqual(
            subscription.package,
            self.package,
        )

        self.assertEqual(
            subscription.billing_cycle,
            SchoolSubscription.BillingCycle.YEARLY,
        )

        self.assertTrue(
            subscription.is_active
        )