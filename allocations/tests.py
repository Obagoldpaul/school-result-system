
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import User
from schools.models import School, SchoolRole, Permission
from academics.models import AcademicSession, Term
from students.models import SchoolClass
from teachers.models import Teacher
from subjects.models import Subject, ClassSubject

from .models import SubjectAllocation
from .forms import SubjectAllocationForm, BulkSubjectAllocationForm


class AllocationTestMixin:
    """
    Shared test data for SubjectAllocation tests.
    """

    def create_school(self, name, code):
        return School.objects.create(
            name=name,
            code=code,
        )

    def create_user(self, school, username, role=User.Role.TEACHER):
        return User.objects.create_user(
            username=username,
            password="TestPassword123!",
            first_name="Test",
            last_name=username,
            school=school,
            role=role,
        )

    def create_teacher(self, school, username, staff_id):
        user = self.create_user(
            school=school,
            username=username,
            role=User.Role.TEACHER,
        )

        return Teacher.objects.create(
            user=user,
            staff_id=staff_id,
        )

    def create_class(self, school, name):
        return SchoolClass.objects.create(
            school=school,
            name=name,
            section=SchoolClass.Section.PRIMARY,
        )

    def create_subject(self, school, name, code):
        return Subject.objects.create(
            school=school,
            name=name,
            code=code,
        )

    def create_term(self, school, session_name="2026/2027"):
        session = AcademicSession.objects.create(
            school=school,
            name=session_name,
            is_current=True,
        )

        return Term.objects.create(
            session=session,
            name=Term.TermName.FIRST,
            is_current=True,
        )


class SubjectAllocationModelTests(AllocationTestMixin, TestCase):
    """
    Tests for the SubjectAllocation model.
    """

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "SCH001",
        )

        self.school2 = self.create_school(
            "School Two",
            "SCH002",
        )

        self.teacher1 = self.create_teacher(
            self.school1,
            "teacher1",
            "ST001",
        )

        self.teacher2 = self.create_teacher(
            self.school2,
            "teacher2",
            "ST002",
        )

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.class2 = self.create_class(
            self.school2,
            "Primary 1",
        )

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "MATH001",
        )

        self.subject2 = self.create_subject(
            self.school2,
            "Mathematics",
            "MATH002",
        )

        self.term1 = self.create_term(self.school1)

        self.term2 = self.create_term(
            self.school2,
            "2026/2027",
        )

    def test_allocation_can_be_created_for_same_school(self):
        allocation = SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.term1,
        )

        self.assertEqual(
            allocation.status,
            SubjectAllocation.Status.DRAFT,
        )

        self.assertEqual(
            allocation.teacher,
            self.teacher1,
        )

    def test_cross_school_teacher_is_rejected(self):
        with self.assertRaises(ValidationError):
            SubjectAllocation.objects.create(
                teacher=self.teacher2,
                subject=self.subject1,
                school_class=self.class1,
                term=self.term1,
            )

    def test_cross_school_subject_is_rejected(self):
        with self.assertRaises(ValidationError):
            SubjectAllocation.objects.create(
                teacher=self.teacher1,
                subject=self.subject2,
                school_class=self.class1,
                term=self.term1,
            )

    def test_cross_school_class_is_rejected(self):
        with self.assertRaises(ValidationError):
            SubjectAllocation.objects.create(
                teacher=self.teacher1,
                subject=self.subject1,
                school_class=self.class2,
                term=self.term1,
            )

    def test_cross_school_term_is_rejected(self):
        with self.assertRaises(ValidationError):
            SubjectAllocation.objects.create(
                teacher=self.teacher1,
                subject=self.subject1,
                school_class=self.class1,
                term=self.term2,
            )

    def test_duplicate_allocation_is_rejected(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.term1,
        )

        with self.assertRaises(Exception):
            SubjectAllocation.objects.create(
                teacher=self.teacher1,
                subject=self.subject1,
                school_class=self.class1,
                term=self.term1,
            )


class SubjectAllocationFormTests(AllocationTestMixin, TestCase):
    """
    Tests school isolation in SubjectAllocationForm.
    """

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "FORM001",
        )

        self.school2 = self.create_school(
            "School Two",
            "FORM002",
        )

        self.teacher1 = self.create_teacher(
            self.school1,
            "formteacher1",
            "FORM-T001",
        )

        self.teacher2 = self.create_teacher(
            self.school2,
            "formteacher2",
            "FORM-T002",
        )

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.class2 = self.create_class(
            self.school2,
            "Primary 1",
        )

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "FORM-M001",
        )

        self.subject2 = self.create_subject(
            self.school2,
            "Mathematics",
            "FORM-M002",
        )

        self.term1 = self.create_term(self.school1)
        self.term2 = self.create_term(self.school2)

        self.user1 = self.create_user(
            self.school1,
            "formadmin1",
            User.Role.ADMIN,
        )

    def test_form_only_contains_same_school_teachers(self):
        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.teacher1,
            form.fields["teacher"].queryset,
        )

        self.assertNotIn(
            self.teacher2,
            form.fields["teacher"].queryset,
        )

    def test_form_only_contains_same_school_subjects(self):
        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.subject1,
            form.fields["subject"].queryset,
        )

        self.assertNotIn(
            self.subject2,
            form.fields["subject"].queryset,
        )

    def test_form_only_contains_same_school_classes(self):
        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.class1,
            form.fields["school_class"].queryset,
        )

        self.assertNotIn(
            self.class2,
            form.fields["school_class"].queryset,
        )

    def test_form_only_contains_same_school_terms(self):
        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.term1,
            form.fields["term"].queryset,
        )

        self.assertNotIn(
            self.term2,
            form.fields["term"].queryset,
        )


class BulkSubjectAllocationFormTests(AllocationTestMixin, TestCase):
    """
    Tests for the bulk allocation form.
    """

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "BULK001",
        )

        self.school2 = self.create_school(
            "School Two",
            "BULK002",
        )

        self.user1 = self.create_user(
            self.school1,
            "bulkadmin1",
            User.Role.ADMIN,
        )

        self.teacher1 = self.create_teacher(
            self.school1,
            "bulkteacher1",
            "BULK-T001",
        )

        self.teacher2 = self.create_teacher(
            self.school2,
            "bulkteacher2",
            "BULK-T002",
        )

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.class2 = self.create_class(
            self.school2,
            "Primary 1",
        )

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "BULK-M001",
        )

        self.subject2 = self.create_subject(
            self.school2,
            "Mathematics",
            "BULK-M002",
        )

        ClassSubject.objects.create(
            school_class=self.class1,
            subject=self.subject1,
        )

        ClassSubject.objects.create(
            school_class=self.class2,
            subject=self.subject2,
        )

        self.term1 = self.create_term(self.school1)
        self.term2 = self.create_term(self.school2)

    def test_bulk_form_only_contains_same_school_classes(self):
        form = BulkSubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.class1,
            form.fields["school_class"].queryset,
        )

        self.assertNotIn(
            self.class2,
            form.fields["school_class"].queryset,
        )

    def test_bulk_form_only_contains_same_school_terms(self):
        form = BulkSubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.term1,
            form.fields["term"].queryset,
        )

        self.assertNotIn(
            self.term2,
            form.fields["term"].queryset,
        )

    def test_get_teachers_only_returns_same_school_teachers(self):
        form = BulkSubjectAllocationForm(
            user=self.user1,
        )

        teachers = form.get_teachers()

        self.assertIn(
            self.teacher1,
            teachers,
        )

        self.assertNotIn(
            self.teacher2,
            teachers,
        )

    def test_get_subjects_returns_subjects_assigned_to_class(self):
        form = BulkSubjectAllocationForm(
            data={
                "school_class": self.class1.id,
                "term": self.term1.id,
            },
            user=self.user1,
        )

        subjects = form.get_subjects()

        self.assertIn(
            self.subject1,
            subjects,
        )

        self.assertNotIn(
            self.subject2,
            subjects,
        )


class AllocationViewSecurityTests(AllocationTestMixin, TestCase):

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "VIEW001",
        )

        self.school2 = self.create_school(
            "School Two",
            "VIEW002",
        )

        # ----------------------------------------
        # PERMISSION / SCHOOL ROLE
        # ----------------------------------------

        self.subjects_view_permission = Permission.objects.create(
            code="subjects.view",
            name="View Subjects",
            module="Subjects",
        )

        self.admin_role = SchoolRole.objects.create(
            school=self.school1,
            name="Test Admin",
        )

        self.admin_role.permissions.add(
            self.subjects_view_permission
        )

        self.admin1 = self.create_user(
            self.school1,
            "viewadmin1",
            User.Role.ADMIN,
        )

        self.admin1.school_role = self.admin_role
        self.admin1.save(update_fields=["school_role"])

        # ----------------------------------------
        # TEACHERS
        # ----------------------------------------

        self.teacher1 = self.create_teacher(
            self.school1,
            "viewteacher1",
            "VIEW-T001",
        )

        self.teacher2 = self.create_teacher(
            self.school2,
            "viewteacher2",
            "VIEW-T002",
        )

        # ----------------------------------------
        # CLASSES
        # ----------------------------------------

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.class2 = self.create_class(
            self.school2,
            "Primary 1",
        )

        # ----------------------------------------
        # SUBJECTS
        # ----------------------------------------

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "VIEW-M001",
        )

        self.subject2 = self.create_subject(
            self.school2,
            "English",
            "VIEW-M002",
        )

        # ----------------------------------------
        # TERMS
        # ----------------------------------------

        self.term1 = self.create_term(self.school1)
        self.term2 = self.create_term(self.school2)

        # ----------------------------------------
        # ALLOCATIONS
        # ----------------------------------------

        self.allocation1 = SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.term1,
        )

        self.allocation2 = SubjectAllocation.objects.create(
            teacher=self.teacher2,
            subject=self.subject2,
            school_class=self.class2,
            term=self.term2,
        )

def test_allocation_list_only_shows_current_school_allocations(self):
    self.client.force_login(self.admin1)

    response = self.client.get(
        reverse("allocation_list")
    )

    self.assertEqual(
        response.status_code,
        200,
    )

    content = response.content.decode()

    self.assertIn(
        self.subject1.name,
        content,
    )

    self.assertNotIn(
        self.subject2.name,
        content,
    )