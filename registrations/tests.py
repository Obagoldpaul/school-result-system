from django.test import TestCase

from accounts.models import User
from registrations.forms import (
    StudentRegistrationApplicationForm,
    TeacherRegistrationApplicationForm,
)
from registrations.models import RegistrationApplication
from schools.models import School
from students.models import Department, SchoolClass


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