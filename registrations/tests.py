from django.test import TestCase

from accounts.models import User
from registrations.forms import (
    StudentRegistrationApplicationForm,
    TeacherRegistrationApplicationForm,
)
from registrations.models import RegistrationApplication
from schools.models import School
from students.models import Department, SchoolClass

from django.urls import reverse
from django.test import override_settings

from accounts.models import User
from schools.models import Permission, School, SchoolRole
from students.models import Department, SchoolClass, Student


class RegistrationApplicationFormTests(TestCase):

    def setUp(self):
        self.school_a = School.objects.create(
            name="School A",
            code="SCHA",
        )

        self.school_b = School.objects.create(
            name="School B",
            code="SCHB",
        )

        self.school_a_class = SchoolClass.objects.create(
            school=self.school_a,
            name="JSS1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        self.school_a_inactive_class = SchoolClass.objects.create(
            school=self.school_a,
            name="JSS2",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=False,
        )

        self.school_b_class = SchoolClass.objects.create(
            school=self.school_b,
            name="JSS1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        self.school_a_department = Department.objects.create(
            school=self.school_a,
            name="Science",
        )

        self.school_b_department = Department.objects.create(
            school=self.school_b,
            name="Arts",
        )

    def get_student_data(self, **overrides):
        data = {
            "username": "newstudent",
            "password": "StrongPassword123!",
            "password_confirmation": "StrongPassword123!",
            "first_name": "John",
            "other_name": "Paul",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "08012345678",
            "date_of_birth": "2012-05-10",
            "gender": "MALE",
            "nationality": "Nigerian",
            "state_of_origin": "Lagos",
            "local_government": "",
            "religion": "Christianity",
            "home_address": "12 Test Street",
            "requested_class": self.school_a_class.pk,
            "requested_department": self.school_a_department.pk,
            "guardian_name": "Jane Doe",
            "guardian_relationship": "Mother",
            "guardian_phone": "08087654321",
            "guardian_email": "jane@example.com",
            "blood_group": "O+",
            "genotype": "AA",
            "medical_condition": "",
            "previous_school": "Previous School",
        }

        data.update(overrides)
        return data

    def get_teacher_data(self, **overrides):
        data = {
            "username": "newteacher",
            "password": "StrongPassword123!",
            "password_confirmation": "StrongPassword123!",
            "first_name": "Jane",
            "other_name": "Mary",
            "last_name": "Doe",
            "email": "jane@example.com",
            "phone_number": "08012345678",
            "date_of_birth": "1990-05-10",
            "gender": "FEMALE",
            "nationality": "Nigerian",
            "state_of_origin": "Lagos",
            "local_government": "",
            "religion": "Christianity",
            "home_address": "12 Teacher Street",
            "qualification": "B.Sc. Mathematics",
            "years_of_experience": 5,
        }

        data.update(overrides)
        return data

    def test_student_form_creates_pending_application(self):
        form = StudentRegistrationApplicationForm(
            data=self.get_student_data(),
            school=self.school_a,
        )

        self.assertTrue(form.is_valid(), form.errors)

        application = form.save()

        self.assertEqual(
            application.school,
            self.school_a,
        )
        self.assertEqual(
            application.role,
            RegistrationApplication.Role.STUDENT,
        )
        self.assertEqual(
            application.status,
            RegistrationApplication.Status.PENDING,
        )
        self.assertEqual(
            application.requested_class,
            self.school_a_class,
        )
        self.assertEqual(
            application.requested_department,
            self.school_a_department,
        )

    def test_teacher_form_creates_pending_application(self):
        form = TeacherRegistrationApplicationForm(
            data=self.get_teacher_data(),
            school=self.school_a,
        )

        self.assertTrue(form.is_valid(), form.errors)

        application = form.save()

        self.assertEqual(
            application.school,
            self.school_a,
        )
        self.assertEqual(
            application.role,
            RegistrationApplication.Role.TEACHER,
        )
        self.assertEqual(
            application.status,
            RegistrationApplication.Status.PENDING,
        )

    def test_student_form_only_shows_active_classes_for_school(self):
        form = StudentRegistrationApplicationForm(
            school=self.school_a,
        )

        available_classes = list(
            form.fields["requested_class"].queryset
        )

        self.assertIn(
            self.school_a_class,
            available_classes,
        )
        self.assertNotIn(
            self.school_a_inactive_class,
            available_classes,
        )
        self.assertNotIn(
            self.school_b_class,
            available_classes,
        )

    def test_student_form_only_shows_departments_for_school(self):
        form = StudentRegistrationApplicationForm(
            school=self.school_a,
        )

        available_departments = list(
            form.fields["requested_department"].queryset
        )

        self.assertIn(
            self.school_a_department,
            available_departments,
        )
        self.assertNotIn(
            self.school_b_department,
            available_departments,
        )

    def test_student_form_rejects_taken_username(self):
        User.objects.create_user(
            username="newstudent",
            password="ExistingPassword123!",
            school=self.school_a,
        )

        form = StudentRegistrationApplicationForm(
            data=self.get_student_data(),
            school=self.school_a,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "username",
            form.errors,
        )

    def test_student_form_rejects_pending_username(self):
        RegistrationApplication.objects.create(
            school=self.school_a,
            role=RegistrationApplication.Role.STUDENT,
            status=RegistrationApplication.Status.PENDING,
            username="newstudent",
            first_name="Existing",
            other_name="",
            last_name="Applicant",
            email="existing@example.com",
            date_of_birth="2012-01-01",
            gender="MALE",
        )

        form = StudentRegistrationApplicationForm(
            data=self.get_student_data(),
            school=self.school_a,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "username",
            form.errors,
        )
        

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class RegistrationApprovalDuplicateWarningTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Approval Test School",
            code="APTS",
        )

        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="JSS1",
            section=SchoolClass.Section.JUNIOR_SECONDARY,
            is_active=True,
        )

        review_permission = Permission.objects.create(
            code="registrations.review",
            name="Review Registrations",
            module="Registration",
            is_active=True,
        )

        view_permission = Permission.objects.create(
            code="registrations.view",
            name="View Registrations",
            module="Registration",
            is_active=True,
        )

        role = SchoolRole.objects.create(
            school=self.school,
            name="Registration Reviewer",
            base_role=SchoolRole.BaseRole.ADMIN,
            is_active=True,
        )
        role.permissions.add(
            review_permission,
            view_permission,
        )

        self.reviewer = User.objects.create_user(
            username="approval-reviewer",
            password="TestPassword123!",
            school=self.school,
            role=User.Role.ADMIN,
            school_role=role,
        )

        self.application = RegistrationApplication.objects.create(
            school=self.school,
            role=RegistrationApplication.Role.STUDENT,
            status=RegistrationApplication.Status.PENDING,
            username="john-doe-applicant",
            first_name="John",
            other_name="",
            last_name="Doe",
            email="john.applicant@example.com",
            date_of_birth="2012-05-10",
            gender="MALE",
            requested_class=self.school_class,
        )

        self.approval_url = reverse(
            "approve_registration_application",
            kwargs={"application_id": self.application.pk},
        )

        self.detail_url = reverse(
            "registration_application_detail",
            kwargs={"application_id": self.application.pk},
        )

        self.client.force_login(self.reviewer)

    def create_matching_user(self, username):
        return User.objects.create_user(
            username=username,
            password="TestPassword123!",
            school=self.school,
            first_name="John",
            last_name="Doe",
        )

    def test_first_approval_attempt_pauses_for_duplicate_review(self):
        self.create_matching_user("existing-john")

        response = self.client.post(self.approval_url)

        self.assertRedirects(response, self.detail_url)

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            RegistrationApplication.Status.PENDING,
        )
        self.assertFalse(
            User.objects.filter(
                username="john-doe-applicant"
            ).exists()
        )
        self.assertTrue(
            self.client.session.get(
                f"registration_duplicate_confirmation_{self.application.pk}"
            )
        )

    def test_reviewer_can_confirm_and_approve_after_reviewing_duplicates(self):
        self.create_matching_user("existing-john")

        self.client.post(self.approval_url)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Possible Duplicate Name Found")
        self.assertContains(response, "Approve Anyway")

        response = self.client.post(self.approval_url)

        self.assertRedirects(response, self.detail_url)

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            RegistrationApplication.Status.APPROVED,
        )
        self.assertEqual(
            self.application.reviewed_by,
            self.reviewer,
        )

        self.assertTrue(
            User.objects.filter(
                username="john-doe-applicant",
                school=self.school,
            ).exists()
        )

        self.assertTrue(
            Student.objects.filter(
                user__username="john-doe-applicant",
                school_class=self.school_class,
            ).exists()
        )

        self.assertNotIn(
            f"registration_duplicate_confirmation_{self.application.pk}",
            self.client.session,
        )

    def test_new_duplicate_requires_another_review_before_approval(self):
        self.create_matching_user("existing-john")

        self.client.post(self.approval_url)

        self.create_matching_user("another-existing-john")

        response = self.client.post(self.approval_url)

        self.assertRedirects(response, self.detail_url)

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            RegistrationApplication.Status.PENDING,
        )
        self.assertFalse(
            User.objects.filter(
                username="john-doe-applicant"
            ).exists()
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approve Anyway")
        self.assertContains(response, "existing-john")
        self.assertContains(response, "another-existing-john")