
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
from .forms import (
    SubjectAllocationForm,
    BulkSubjectAllocationForm,
    CarryForwardAllocationForm,
)


from datetime import timedelta
from django.utils import timezone

from schools.models import (
    School,
    SchoolRole,
    Permission,
    SubscriptionPackage,
    SchoolSubscription,
)

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
    
    def test_form_excludes_inactive_classes(self):
        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertNotIn(
            self.class1,
            form.fields["school_class"].queryset,
        )


    def test_form_still_includes_active_classes(self):
        form = SubjectAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.class1,
            form.fields["school_class"].queryset,
        )     



class CarryForwardAllocationFormTests(AllocationTestMixin, TestCase):
    """
    Tests for the carry-forward allocation form.
    """

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "CARRY001",
        )

        self.school2 = self.create_school(
            "School Two",
            "CARRY002",
        )

        self.user1 = self.create_user(
            self.school1,
            "carryadmin1",
            User.Role.ADMIN,
        )

        # ----------------------------------------
        # CURRENT SESSION / TERMS
        # ----------------------------------------

        self.session1 = AcademicSession.objects.create(
            school=self.school1,
            name="2026/2027",
            is_current=True,
        )

        self.first_term = Term.objects.create(
            session=self.session1,
            name=Term.TermName.FIRST,
            is_current=False,
        )

        self.second_term = Term.objects.create(
            session=self.session1,
            name=Term.TermName.SECOND,
            is_current=True,
        )

        self.third_term = Term.objects.create(
            session=self.session1,
            name=Term.TermName.THIRD,
            is_current=False,
        )

        # ----------------------------------------
        # PREVIOUS SESSION
        # ----------------------------------------

        self.session2 = AcademicSession.objects.create(
            school=self.school1,
            name="2025/2026",
            is_current=False,
        )

        self.previous_third_term = Term.objects.create(
            session=self.session2,
            name=Term.TermName.THIRD,
            is_current=False,
        )

        # ----------------------------------------
        # OTHER SCHOOL
        # ----------------------------------------

        self.other_session = AcademicSession.objects.create(
            school=self.school2,
            name="2026/2027",
            is_current=True,
        )

        self.other_term = Term.objects.create(
            session=self.other_session,
            name=Term.TermName.FIRST,
            is_current=True,
        )

    def test_form_only_contains_same_school_sessions_and_terms(self):
        form = CarryForwardAllocationForm(
            user=self.user1,
        )

        self.assertIn(
            self.session1,
            form.fields["from_session"].queryset,
        )

        self.assertIn(
            self.session1,
            form.fields["to_session"].queryset,
        )

        self.assertIn(
            self.first_term,
            form.fields["from_term"].queryset,
        )

        self.assertIn(
            self.second_term,
            form.fields["to_term"].queryset,
        )

        self.assertNotIn(
            self.other_session,
            form.fields["from_session"].queryset,
        )

        self.assertNotIn(
            self.other_session,
            form.fields["to_session"].queryset,
        )

        self.assertNotIn(
            self.other_term,
            form.fields["from_term"].queryset,
        )

        self.assertNotIn(
            self.other_term,
            form.fields["to_term"].queryset,
        )

    def test_second_term_defaults_to_first_term_and_current_term(self):
        form = CarryForwardAllocationForm(
            user=self.user1,
        )

        self.assertEqual(
            form.initial["from_session"],
            self.session1,
        )

        self.assertEqual(
            form.initial["from_term"],
            self.first_term,
        )

        self.assertEqual(
            form.initial["to_session"],
            self.session1,
        )

        self.assertEqual(
            form.initial["to_term"],
            self.second_term,
        )

    def test_same_term_is_rejected(self):
        form = CarryForwardAllocationForm(
            data={
                "from_session": self.session1.pk,
                "from_term": self.second_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.second_term.pk,
            },
            user=self.user1,
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "__all__",
            form.errors,
        )

    def test_cross_school_terms_are_rejected(self):
        form = CarryForwardAllocationForm(
            data={
                "from_session": self.session1.pk,
                "from_term": self.first_term.pk,
                "to_session": self.other_session.pk,
                "to_term": self.other_term.pk,
            },
            user=self.user1,
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "to_session",
            form.errors,
        )

        self.assertIn(
            "to_term",
            form.errors,
        )

    def test_term_must_belong_to_selected_session(self):
        form = CarryForwardAllocationForm(
            data={
                "from_session": self.session1.pk,
                "from_term": self.first_term.pk,
                "to_session": self.session2.pk,
                "to_term": self.first_term.pk,
            },
            user=self.user1,
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "to_term",
            form.errors,
        )

    def test_first_term_defaults_to_previous_session_third_term(self):
        self.first_term.is_current = True
        self.first_term.save(update_fields=["is_current"])

        self.second_term.is_current = False
        self.second_term.save(update_fields=["is_current"])

        form = CarryForwardAllocationForm(
            user=self.user1,
        )

        self.assertEqual(
            form.initial["from_session"],
            self.session2,
        )

        self.assertEqual(
            form.initial["from_term"],
            self.previous_third_term,
        )

        self.assertEqual(
            form.initial["to_session"],
            self.session1,
        )

        self.assertEqual(
            form.initial["to_term"],
            self.first_term,
        )


class CarryForwardAllocationViewTests(AllocationTestMixin, TestCase):
    """
    Tests for the carry-forward allocation view.
    """

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "CARRYVIEW001",
        )
        
        self.subscription_package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=self.school1,
            package=self.subscription_package,
            billing_cycle=SchoolSubscription.BillingCycle.TERMLY,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            is_active=True,
        )

        self.school2 = self.create_school(
            "School Two",
            "CARRYVIEW002",
        )

        # ----------------------------------------
        # PERMISSION
        # ----------------------------------------

        self.assign_permission = Permission.objects.create(
            code="subjects.assign",
            name="Assign Subjects",
            module="Subjects",
        )

        self.admin_role = SchoolRole.objects.create(
            school=self.school1,
            name="Carry Forward Admin",
        )

        self.admin_role.permissions.add(
            self.assign_permission
        )

        self.admin1 = self.create_user(
            self.school1,
            "carryviewadmin1",
            User.Role.ADMIN,
        )

        self.admin1.school_role = self.admin_role
        self.admin1.save(update_fields=["school_role"])

        self.admin_without_permission = self.create_user(
            self.school1,
            "carryviewadmin2",
            User.Role.ADMIN,
        )

        # ----------------------------------------
        # TEACHERS
        # ----------------------------------------

        self.teacher1 = self.create_teacher(
            self.school1,
            "carryviewteacher1",
            "CV-T001",
        )
        
        self.teacher1_existing = self.create_teacher(
            self.school1,
            "carryviewteacher1existing",
            "CV-T003",
        )

        self.teacher2 = self.create_teacher(
            self.school2,
            "carryviewteacher2",
            "CV-T002",
        )

        # ----------------------------------------
        # CLASSES
        # ----------------------------------------

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.class2 = self.create_class(
            self.school1,
            "Primary 2",
        )

        self.other_school_class = self.create_class(
            self.school2,
            "Primary 1",
        )

        # ----------------------------------------
        # SUBJECTS
        # ----------------------------------------

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "CV-M001",
        )

        self.subject2 = self.create_subject(
            self.school1,
            "English",
            "CV-M002",
        )

        self.other_school_subject = self.create_subject(
            self.school2,
            "Mathematics",
            "CV-M003",
        )

        # ----------------------------------------
        # TERMS
        # ----------------------------------------

        self.session1 = AcademicSession.objects.create(
            school=self.school1,
            name="2026/2027",
            is_current=True,
        )

        self.from_term = Term.objects.create(
            session=self.session1,
            name=Term.TermName.FIRST,
            is_current=False,
        )

        self.to_term = Term.objects.create(
            session=self.session1,
            name=Term.TermName.SECOND,
            is_current=True,
        )

        self.other_session = AcademicSession.objects.create(
            school=self.school2,
            name="2026/2027",
            is_current=True,
        )

        self.other_term = Term.objects.create(
            session=self.other_session,
            name=Term.TermName.FIRST,
            is_current=True,
        )

    def test_copies_missing_allocations(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.from_term,
        )

        self.client.force_login(self.admin1)

        response = self.client.post(
            reverse("carry_forward_allocations"),
            {
                
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.to_term.pk,

            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        allocation = SubjectAllocation.objects.get(
            subject=self.subject1,
            school_class=self.class1,
            term=self.to_term,
        )

        self.assertEqual(
            allocation.teacher,
            self.teacher1,
        )

    def test_new_allocations_are_draft(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.from_term,
        )

        self.client.force_login(self.admin1)

        self.client.post(
            reverse("carry_forward_allocations"),
            {
                
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.to_term.pk,

            },
        )

        allocation = SubjectAllocation.objects.get(
            subject=self.subject1,
            school_class=self.class1,
            term=self.to_term,
        )

        self.assertEqual(
            allocation.status,
            SubjectAllocation.Status.DRAFT,
        )

    def test_does_not_overwrite_existing_destination_allocations(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.from_term,
        )

        existing_destination = SubjectAllocation.objects.create(
            teacher=self.teacher1_existing,
            subject=self.subject1,
            school_class=self.class1,
            term=self.to_term,
        )

        self.client.force_login(self.admin1)

        self.client.post(
            reverse("carry_forward_allocations"),
            {
            
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.to_term.pk,

            },
        )

        destination_allocations = SubjectAllocation.objects.filter(
            subject=self.subject1,
            school_class=self.class1,
            term=self.to_term,
        )

        self.assertEqual(
            destination_allocations.count(),
            1,
        )

        existing_destination.refresh_from_db()

        self.assertEqual(
            existing_destination.teacher,
            self.teacher1_existing,
        )

    def test_does_not_copy_allocations_from_another_school(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher2,
            subject=self.other_school_subject,
            school_class=self.other_school_class,
            term=self.other_term,
        )

        self.client.force_login(self.admin1)

        response = self.client.post(
            reverse("carry_forward_allocations"),
            {
                
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.to_term.pk,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            SubjectAllocation.objects.filter(
                subject=self.other_school_subject,
                school_class=self.other_school_class,
                term=self.to_term,
            ).exists()
        )

    def test_same_source_and_destination_terms_are_rejected(self):
        self.client.force_login(self.admin1)

        response = self.client.post(
            reverse("carry_forward_allocations"),
            {
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.from_term.pk,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            SubjectAllocation.objects.filter(
                term=self.from_term,
            ).count(),
            0,
        )

    def test_view_requires_subjects_assign_permission(self):
        SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.from_term,
        )

        self.client.force_login(
            self.admin_without_permission
        )

        response = self.client.post(
            reverse("carry_forward_allocations"),
            {
                "from_session": self.session1.pk,
                "from_term": self.from_term.pk,
                "to_session": self.session1.pk,
                "to_term": self.to_term.pk,
            },
        )

        self.assertNotEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            SubjectAllocation.objects.filter(
                subject=self.subject1,
                school_class=self.class1,
                term=self.to_term,
            ).exists()
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

