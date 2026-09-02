from django.core.management import call_command
from django.test import TestCase

from schools.models import School, SchoolRole
from schools.views import setup_new_school
from students.models import SchoolClass


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
            16,
        )

        self.assertEqual(
            SchoolRole.objects.filter(school=school).count(),
            4,
        )

        expected_permissions = {
            "Principal": 45,
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

        self.assertEqual(first_class_count, 16)
        self.assertEqual(first_role_count, 4)
        self.assertEqual(second_class_count, first_class_count)
        self.assertEqual(second_role_count, first_role_count)
