from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import (
    School,
    SchoolRole,
    Permission,
    SubscriptionPackage,
    SchoolSubscription,
)
from django.utils import timezone
from academics.models import AcademicSession, Term
from students.models import SchoolClass
from teachers.models import Teacher
from subjects.models import Subject

from allocations.models import SubjectAllocation


class ScorePermissionTestMixin:

    def create_school(self, name, code):
        return School.objects.create(
            name=name,
            code=code,
        )

    def create_user(
        self,
        school,
        username,
        role=User.Role.TEACHER,
    ):
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

    def create_term(self, school):
        session = AcademicSession.objects.create(
            school=school,
            name="2026/2027",
            is_current=True,
        )

        return Term.objects.create(
            session=session,
            name=Term.TermName.FIRST,
            is_current=True,
        )


class ScorePermissionTests(ScorePermissionTestMixin, TestCase):

    def setUp(self):
        self.school1 = self.create_school(
            "School One",
            "SCORE001",
        )

        self.school2 = self.create_school(
            "School Two",
            "SCORE002",
        )
        
        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.BASIC,
        )

        SchoolSubscription.objects.create(
            school=self.school1,
            package=self.package,
            start_date=timezone.now().date(),
        )

        self.view_permission = Permission.objects.create(
            code="scores.view",
            name="View Scores",
            module="Scores",
        )

        self.enter_permission = Permission.objects.create(
            code="scores.enter",
            name="Enter Scores",
            module="Scores",
        )

        self.submit_permission = Permission.objects.create(
            code="scores.submit",
            name="Submit Scores",
            module="Scores",
        )

        self.review_permission = Permission.objects.create(
            code="scores.review",
            name="Review Scores",
            module="Scores",
        )

        self.approve_permission = Permission.objects.create(
            code="scores.approve",
            name="Approve Results",
            module="Scores",
        )

        self.publish_permission = Permission.objects.create(
            code="scores.publish",
            name="Publish Results",
            module="Scores",
        )

        self.role = SchoolRole.objects.create(
            school=self.school1,
            name="Scores Manager",
        )

        self.user = self.create_user(
            self.school1,
            "scoreuser",
            User.Role.ADMIN,
        )

        self.user.school_role = self.role
        self.user.save(update_fields=["school_role"])

        self.teacher1 = self.create_teacher(
            self.school1,
            "scoreteacher1",
            "SCORE-T001",
        )

        self.class1 = self.create_class(
            self.school1,
            "Primary 1",
        )

        self.subject1 = self.create_subject(
            self.school1,
            "Mathematics",
            "SCORE-M001",
        )

        self.term1 = self.create_term(
            self.school1,
        )

        self.allocation = SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=self.class1,
            term=self.term1,
        )

    def grant(self, permission):
        self.role.permissions.add(permission)

    def test_scores_view_permission_allows_select_allocation(self):
        self.grant(self.view_permission)

        self.client.force_login(self.user)

        response = self.client.get(
            reverse("select_allocation")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_scores_view_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("select_allocation")
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_scores_enter_permission_allows_enter_scores(self):
        self.grant(self.enter_permission)

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "enter_scores",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_scores_enter_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "enter_scores",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_scores_submit_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "submit_allocation",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_scores_review_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "review_allocation",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_scores_approve_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "approve_allocation",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_scores_publish_permission_denies_without_permission(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "publish_allocation",
                kwargs={
                    "allocation_id": self.allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )