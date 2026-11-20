from django.test import TestCase, Client, override_settings
from django.core import mail
from django.urls import reverse
from django.test import override_settings
from accounts.models import User
from accounts.permissions import user_has_permission
from schools.models import School, SchoolRole, Permission, SchoolDomain
from django.contrib.auth.models import AnonymousUser
from accounts.duplicate_names import find_possible_duplicate_names
from registrations.models import RegistrationApplication
from academics.models import SchoolSettings

from accounts.permissions import (
    user_has_permission,
    is_management,
)

from accounts.utils import is_management_user

class UserPermissionTests(TestCase):

    def setUp(self):
        # ---------------------------------------------------------
        # SCHOOL A
        # ---------------------------------------------------------
        self.school_a = School.objects.create(
            name="School A",
            code="SCHA",
        )

        self.school_a_role = SchoolRole.objects.create(
            school=self.school_a,
            name="Bursar",
        )

        # ---------------------------------------------------------
        # SCHOOL B
        # ---------------------------------------------------------
        self.school_b = School.objects.create(
            name="School B",
            code="SCHB",
        )

        self.school_b_role = SchoolRole.objects.create(
            school=self.school_b,
            name="Bursar",
        )

        # ---------------------------------------------------------
        # PERMISSIONS
        # ---------------------------------------------------------
        self.billing_view = Permission.objects.create(
            code="billing.view",
            name="View Billing",
            module="Billing",
            is_active=True,
        )

        self.billing_record_payment = Permission.objects.create(
            code="billing.record_payment",
            name="Record Payments",
            module="Billing",
            is_active=True,
        )

        self.billing_delete_payment = Permission.objects.create(
            code="billing.delete_payment",
            name="Delete Payments",
            module="Billing",
            is_active=True,
        )

        # School A's Bursar can view billing
        # and record payments.
        self.school_a_role.permissions.add(
            self.billing_view,
            self.billing_record_payment,
        )

        # School B's Bursar gets only the delete permission.
        self.school_b_role.permissions.add(
            self.billing_delete_payment,
        )

        # ---------------------------------------------------------
        # USERS
        # ---------------------------------------------------------
        self.school_a_user = User.objects.create_user(
            username="school-a-bursar",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
            school_role=self.school_a_role,
        )

        self.school_b_user = User.objects.create_user(
            username="school-b-bursar",
            password="testpass123",
            school=self.school_b,
            role=User.Role.TEACHER,
            school_role=self.school_b_role,
        )

    def test_user_can_use_permission_assigned_to_role(self):
        """A user should receive permissions from their SchoolRole."""

        self.assertTrue(
            user_has_permission(
                self.school_a_user,
                "billing.view",
            )
        )

        self.assertTrue(
            user_has_permission(
                self.school_a_user,
                "billing.record_payment",
            )
        )

    def test_user_cannot_use_permission_not_assigned_to_role(self):
        """A user cannot perform actions their role was not given."""

        self.assertFalse(
            user_has_permission(
                self.school_a_user,
                "billing.delete_payment",
            )
        )

    def test_school_role_isolation(self):
        """
        A user's role must belong to the same school as the user.
        """

        # Temporarily give School B's role to School A's user.
        self.school_a_user.school_role = self.school_b_role
        self.school_a_user.save(update_fields=["school_role"])

        self.assertFalse(
            user_has_permission(
                self.school_a_user,
                "billing.delete_payment",
            )
        )

    def test_inactive_role_has_no_permissions(self):
        """An inactive SchoolRole must not grant permissions."""

        self.school_a_role.is_active = False
        self.school_a_role.save(update_fields=["is_active"])

        self.assertFalse(
            user_has_permission(
                self.school_a_user,
                "billing.view",
            )
        )

    def test_unauthenticated_user_has_no_permission(self):
        """Anonymous users must never receive SchoolRole permissions."""

        self.school_a_user.is_active = False

        self.assertFalse(
            user_has_permission(
                None,
                "billing.view",
            )
        )
        

    def test_management_roles_are_recognized(self):
        """
        All approved school management roles should be
        recognized as management users.
        """

        management_roles = [
            "Proprietor",
            "Proprietoress",
            "Principal",
            "Vice Principal",
            "Head Teacher",
            "Assistant Head Teacher",
            "Headmaster",
            "Headmistress",
            "School Manager",
        ]

        for role_name in management_roles:
            with self.subTest(role=role_name):
                role = SchoolRole.objects.create(
                    school=self.school_a,
                    name=role_name,
                    base_role=SchoolRole.BaseRole.ADMIN,
                )

                user = User.objects.create_user(
                    username=(
                        "management-"
                        + role_name.lower().replace(" ", "-")
                    ),
                    password="testpass123",
                    school=self.school_a,
                    role=User.Role.TEACHER,
                    school_role=role,
                )

                self.assertTrue(
                    is_management(user)
                )

    def test_bursar_is_not_management(self):
        """Bursar should remain separate from general management."""

        self.assertFalse(
            is_management(self.school_a_user)
        )

    def test_teacher_without_management_role_is_not_management(self):
        """A normal teacher should not be treated as management."""

        teacher = User.objects.create_user(
            username="regular-teacher",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
        )

        self.assertFalse(
            is_management(teacher)
        )

    def test_student_is_not_management(self):
        """A student should not be treated as management."""

        student = User.objects.create_user(
            username="school-student",
            password="testpass123",
            school=self.school_a,
            role=User.Role.STUDENT,
        )

        self.assertFalse(
            is_management(student)
        )

    def test_inactive_management_role_is_not_management(self):
        """An inactive management role should not grant management status."""

        role = SchoolRole.objects.create(
            school=self.school_a,
            name="Principal",
            base_role=SchoolRole.BaseRole.ADMIN,
            is_active=False,
        )

        user = User.objects.create_user(
            username="inactive-principal",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
            school_role=role,
        )

        self.assertFalse(
            is_management(user)
        )

    def test_management_role_must_belong_to_same_school(self):
        """
        A management role belonging to another school must not
        make the user a management user.
        """

        role = SchoolRole.objects.create(
            school=self.school_b,
            name="Principal",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        user = User.objects.create_user(
            username="wrong-school-principal",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
            school_role=role,
        )

        self.assertFalse(
            is_management(user)
        )

    def test_unauthenticated_user_is_not_management(self):
        self.assertFalse(
            is_management(AnonymousUser())
        )
        
    def test_is_management_user_matches_management_status(self):
        management_role = SchoolRole.objects.create(
            school=self.school_a,
            name="Head Teacher",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        management_user = User.objects.create_user(
            username="dashboard-management",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
            school_role=management_role,
        )

        self.assertTrue(is_management_user(management_user))

        teacher = User.objects.create_user(
            username="dashboard-teacher",
            password="testpass123",
            school=self.school_a,
            role=User.Role.TEACHER,
        )

        self.assertFalse(is_management_user(teacher))
        
        
class PasswordResetEmailTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Great Goshenland Blossom School",
            code="GGBS",
            email="office@ggbs.example",
            phone="08012345678",
        )

        self.user = User.objects.create_user(
            username="reset-test-user",
            email="reset-test@example.com",
            password="ExistingPassword123!",
            school=self.school,
            role=User.Role.TEACHER,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    
    def test_reset_request_preserves_school_code_in_success_redirect(self):
        response = self.client.post(
            f"{reverse('password_reset')}?school={self.school.code}",
            {"email": self.user.email},
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            f"{reverse('password_reset_done')}?school={self.school.code}",
        )
    
    def test_password_reset_done_page_resolves_school_from_query_parameter(self):
        response = self.client.get(
            reverse("password_reset_done"),
            {"school": self.school.code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["login_school"],
            self.school,
        )
    
    def test_password_reset_page_resolves_school_from_query_parameter(self):
        response = self.client.get(
            reverse("password_reset"),
            {"school": self.school.code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["login_school"],
            self.school,
        )
    def test_reset_email_uses_school_name_and_platform_domain(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.subject,
            "Great Goshenland Blossom School - Reset Your Password",
        )

        self.assertIn(
            "https://paulschoolhub.com.ng/set-password/",
            email.body,
        )
        
        self.assertEqual(
            email.from_email,
            "Great Goshenland Blossom School via Paul SchoolHub "
            "<noreply@paulschoolhub.com.ng>",
        )

        self.assertEqual(
            email.extra_headers.get("Reply-To"),
            "office@ggbs.example",
        )

        self.assertEqual(
            email.cc,
            ["noreply@paulschoolhub.com.ng"],
        )

        self.assertIn("office@ggbs.example", email.body)
        self.assertIn("08012345678", email.body)


    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_reset_email_uses_fallback_without_school(self):
        user_without_school = User.objects.create_user(
            username="no-school-reset-user",
            email="no-school-reset@example.com",
            password="ExistingPassword123!",
            school=None,
            role=User.Role.TEACHER,
        )

        self.client.post(
            reverse("password_reset"),
            {"email": user_without_school.email},
        )

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            mail.outbox[0].subject,
            "Paul SchoolHub - Reset Your Password",
        )
        
        email = mail.outbox[0]

        self.assertEqual(
            email.from_email,
            "Paul SchoolHub <noreply@paulschoolhub.com.ng>",
        )

        self.assertEqual(
            email.cc,
            ["noreply@paulschoolhub.com.ng"],
        )

        self.assertEqual(email.reply_to, [])

class DuplicateNameCheckerTests(TestCase):

    def setUp(self):
        from datetime import date

        self.school_a = School.objects.create(
            name="Duplicate Test School A",
            code="DUPA",
        )

        self.school_b = School.objects.create(
            name="Duplicate Test School B",
            code="DUPB",
        )

        self.date_of_birth = date(2010, 5, 15)

    def create_user(
        self,
        username,
        school,
        first_name="John",
        last_name="Doe",
    ):
        return User.objects.create_user(
            username=username,
            password="testpass123",
            school=school,
            first_name=first_name,
            last_name=last_name,
        )

    def create_application(
        self,
        username,
        school,
        role=RegistrationApplication.Role.STUDENT,
        status=RegistrationApplication.Status.PENDING,
        first_name="John",
        last_name="Doe",
    ):
        return RegistrationApplication.objects.create(
            school=school,
            role=role,
            status=status,
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@example.com",
            date_of_birth=self.date_of_birth,
            gender="MALE",
        )

    def test_finds_existing_user_with_matching_names(self):
        self.create_user("john-doe", self.school_a)

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
        )

        self.assertEqual(len(result["users"]), 1)
        self.assertEqual(result["users"][0]["username"], "john-doe")
        self.assertEqual(result["applications"], [])

    def test_finds_pending_student_and_teacher_applications(self):
        self.create_application(
            "student-applicant",
            self.school_a,
            role=RegistrationApplication.Role.STUDENT,
        )

        self.create_application(
            "teacher-applicant",
            self.school_a,
            role=RegistrationApplication.Role.TEACHER,
        )

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
        )

        self.assertEqual(result["users"], [])
        self.assertEqual(len(result["applications"]), 2)

        roles = {
            application["role"]
            for application in result["applications"]
        }

        self.assertEqual(
            roles,
            {
                RegistrationApplication.Role.STUDENT,
                RegistrationApplication.Role.TEACHER,
            },
        )

    def test_matching_ignores_case_and_surrounding_whitespace(self):
        self.create_user(
            "john-whitespace",
            self.school_a,
            first_name="  jOHN ",
            last_name=" DOE  ",
        )

        result = find_possible_duplicate_names(
            self.school_a,
            " John ",
            " doe ",
        )

        self.assertEqual(len(result["users"]), 1)

    def test_does_not_match_users_from_another_school(self):
        self.create_user("other-school-user", self.school_b)

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
        )

        self.assertEqual(result["users"], [])
        self.assertEqual(result["applications"], [])

    def test_does_not_match_applications_from_another_school(self):
        self.create_application(
            "other-school-applicant",
            self.school_b,
        )

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
        )

        self.assertEqual(result["applications"], [])

    def test_ignores_approved_and_rejected_applications(self):
        self.create_application(
            "approved-applicant",
            self.school_a,
            status=RegistrationApplication.Status.APPROVED,
        )

        self.create_application(
            "rejected-applicant",
            self.school_a,
            status=RegistrationApplication.Status.REJECTED,
        )

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
        )

        self.assertEqual(result["applications"], [])

    def test_can_exclude_existing_user(self):
        user = self.create_user("current-user", self.school_a)

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
            exclude_user=user,
        )

        self.assertEqual(result["users"], [])

    def test_can_exclude_current_application(self):
        application = self.create_application(
            "current-application",
            self.school_a,
        )

        result = find_possible_duplicate_names(
            self.school_a,
            "John",
            "Doe",
            exclude_application=application,
        )

        self.assertEqual(result["applications"], [])

    def test_returns_no_matches_when_either_name_is_blank(self):
        self.create_user("john-doe", self.school_a)
        self.create_application("john-application", self.school_a)

        result = find_possible_duplicate_names(
            self.school_a,
            "",
            "Doe",
        )

        self.assertEqual(result, {
            "users": [],
            "applications": [],
        })
        
@override_settings(ALLOWED_HOSTS=[".example.com", "testserver", "localhost"])
class DuplicateNameEndpointTests(TestCase):

    def setUp(self):
        self.client = Client()

        self.school_a = School.objects.create(
            name="Endpoint Test School A",
            code="EPA",
        )

        self.school_b = School.objects.create(
            name="Endpoint Test School B",
            code="EPB",
        )

        SchoolDomain.objects.create(
            school=self.school_a,
            domain="school-a.example.com",
            is_primary=True,
            is_active=True,
        )

        SchoolDomain.objects.create(
            school=self.school_b,
            domain="school-b.example.com",
            is_primary=True,
            is_active=True,
        )

        SchoolSettings.objects.create(
            school=self.school_a,
            school_name=self.school_a.name,
        )

        SchoolSettings.objects.create(
            school=self.school_b,
            school_name=self.school_b.name,
        )

    def create_permission(self, code):
        return Permission.objects.create(
            code=code,
            name=code.replace(".", " ").title(),
            module="Registration",
            is_active=True,
        )

    def create_school_user(self, school, permission_code=None):
        role = SchoolRole.objects.create(
            school=school,
            name="Registration Manager",
            base_role=SchoolRole.BaseRole.ADMIN,
        )

        if permission_code:
            permission = self.create_permission(permission_code)
            role.permissions.add(permission)

        return User.objects.create_user(
            username=f"manager-{school.code.lower()}",
            password="testpass123",
            school=school,
            role=User.Role.ADMIN,
            school_role=role,
        )

    def create_matching_user(self, school):
        return User.objects.create_user(
            username=f"existing-{school.code.lower()}",
            password="testpass123",
            school=school,
            first_name="John",
            last_name="Doe",
        )

    def test_authenticated_school_user_can_check_student_names(self):
        user = self.create_school_user(
            self.school_a,
            "students.add",
        )
        self.create_matching_user(self.school_a)

        self.client.force_login(user)

        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "student",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "has_duplicates": True,
                "user_count": 1,
                "application_count": 0,
                "total_count": 1,
            },
        )

    def test_authenticated_school_user_without_permission_is_denied(self):
        user = self.create_school_user(self.school_a)
        self.client.force_login(user)

        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "student",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_public_registration_uses_school_from_domain(self):
        self.create_matching_user(self.school_a)

        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "student",
                "first_name": "John",
                "last_name": "Doe",
            },
            HTTP_HOST="school-a.example.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "has_duplicates": True,
                "user_count": 1,
                "application_count": 0,
                "total_count": 1,
            },
        )

    def test_public_registration_does_not_match_another_school(self):
        self.create_matching_user(self.school_b)

        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "student",
                "first_name": "John",
                "last_name": "Doe",
            },
            HTTP_HOST="school-a.example.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "has_duplicates": False,
                "user_count": 0,
                "application_count": 0,
                "total_count": 0,
            },
        )

    def test_public_registration_is_denied_when_disabled(self):
        settings = SchoolSettings.objects.get(school=self.school_a)
        settings.student_registration_enabled = False
        settings.save()

        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "student",
                "first_name": "John",
                "last_name": "Doe",
            },
            HTTP_HOST="school-a.example.com",
        )

        self.assertEqual(response.status_code, 403)

    def test_platform_admin_can_check_names_for_selected_school(self):
        platform_admin = User.objects.create_user(
            username="endpoint-platform-admin",
            password="testpass123",
            role=User.Role.PLATFORM_ADMIN,
        )

        self.create_matching_user(self.school_a)
        self.client.force_login(platform_admin)

        response = self.client.get(
            reverse(
                "school_duplicate_name_check",
                kwargs={"school_id": self.school_a.pk},
            ),
            {
                "type": "admin",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "has_duplicates": True,
                "user_count": 1,
                "application_count": 0,
                "total_count": 1,
            },
        )

    def test_non_platform_admin_cannot_check_selected_school(self):
        user = self.create_school_user(
            self.school_a,
            "students.add",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "school_duplicate_name_check",
                kwargs={"school_id": self.school_a.pk},
            ),
            {
                "type": "admin",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_registration_type_is_rejected(self):
        response = self.client.get(
            reverse("duplicate_name_check"),
            {
                "type": "unknown",
                "first_name": "John",
                "last_name": "Doe",
            },
        )

        self.assertEqual(response.status_code, 400)
        
@override_settings(ALLOWED_HOSTS=[".example.com", "testserver", "localhost"])
class UsernameAvailabilityEndpointTests(TestCase):

    def setUp(self):
        from datetime import date

        self.client = Client()

        self.school = School.objects.create(
            name="Username Availability Test School",
            code="UATS",
        )

        SchoolDomain.objects.create(
            school=self.school,
            domain="username-school.example.com",
            is_primary=True,
            is_active=True,
        )

        SchoolSettings.objects.create(
            school=self.school,
            school_name=self.school.name,
        )

        self.date_of_birth = date(2010, 5, 15)

    def check_username(self, username):
        return self.client.get(
            reverse("username_availability_check"),
            {
                "type": "student",
                "username": username,
            },
            HTTP_HOST="username-school.example.com",
        )

    def create_application(self, username):
        return RegistrationApplication.objects.create(
            school=self.school,
            role=RegistrationApplication.Role.STUDENT,
            status=RegistrationApplication.Status.PENDING,
            username=username,
            first_name="John",
            last_name="Doe",
            email=f"{username}@example.com",
            date_of_birth=self.date_of_birth,
            gender="MALE",
        )

    def test_available_username_is_accepted(self):
        response = self.check_username("new_student01")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertTrue(response.json()["available"])

    def test_existing_username_is_unavailable_case_insensitively(self):
        User.objects.create_user(
            username="ExistingStudent",
            password="testpass123",
        )

        response = self.check_username("existingstudent")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])
        self.assertFalse(response.json()["available"])

    def test_pending_application_username_is_unavailable(self):
        self.create_application("pending_student")

        response = self.check_username("PENDING_STUDENT")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])

    def test_invalid_username_format_is_rejected(self):
        response = self.check_username("invalid username")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertFalse(response.json()["available"])

    def test_blank_username_is_rejected(self):
        response = self.check_username("")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])
        self.assertFalse(response.json()["available"])

    def test_disabled_registration_is_denied(self):
        settings = SchoolSettings.objects.get(school=self.school)
        settings.student_registration_enabled = False
        settings.save()

        response = self.check_username("new_student01")

        self.assertEqual(response.status_code, 403)

    def test_response_does_not_expose_account_details(self):
        User.objects.create_user(
            username="private_student",
            password="testpass123",
        )

        response = self.check_username("private_student")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json().keys()),
            {"valid", "available", "message"},
        )
        self.assertNotIn("username", response.json())
        self.assertNotIn("user_id", response.json())
        self.assertNotIn("application_id", response.json())