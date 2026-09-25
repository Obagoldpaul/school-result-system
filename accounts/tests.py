from django.test import TestCase

from accounts.models import User
from accounts.permissions import user_has_permission
from schools.models import School, SchoolRole, Permission
from django.contrib.auth.models import AnonymousUser

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