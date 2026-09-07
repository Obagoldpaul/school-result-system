from django.test import TestCase
from django.urls import reverse
from students.models import Student
from .models import Score
from academics.models import SchoolSettings

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
        
        SchoolSettings.objects.create(
            school=self.school1,
            school_name="School One",
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
        
        

    def test_inactive_class_excluded_from_score_allocation_selection(self):
        self.grant(self.view_permission)

        inactive_class = SchoolClass.objects.create(
            school=self.school1,
            name="Primary 2",
            section=SchoolClass.Section.PRIMARY,
            is_active=False,
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse("select_allocation")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            self.class1.name,
        )

        self.assertNotContains(
            response,
            inactive_class.name,
        )


    def test_inactive_class_cannot_access_enter_scores(self):
        self.grant(self.enter_permission)

        inactive_class = SchoolClass.objects.create(
            school=self.school1,
            name="Primary 2",
            section=SchoolClass.Section.PRIMARY,
            is_active=False,
        )

        inactive_allocation = SubjectAllocation.objects.create(
            teacher=self.teacher1,
            subject=self.subject1,
            school_class=inactive_class,
            term=self.term1,
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "enter_scores",
                kwargs={
                    "allocation_id": inactive_allocation.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


    def test_active_class_can_access_enter_scores(self):
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
        
    def test_scores_are_preserved_when_class_is_deactivated(self):
        """Deactivating a class must not delete its existing scores."""
        student_user = self.create_user(
            self.school1,
            "historicalstudent",
            User.Role.STUDENT,
        )

        student = Student.objects.create(
            user=student_user,
            school_class=self.class1,
            admission_number="HIST001",
        )

        score = Score.objects.create(
            student=student,
            subject=self.subject1,
            term=self.term1,
            ca_score=30,
            exam_score=50,
            recorded_by=self.teacher1,
        )

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        score.refresh_from_db()

        self.assertEqual(score.ca_score, 30)
        self.assertEqual(score.exam_score, 50)
        self.assertEqual(score.student_id, student.id)
        self.assertEqual(score.subject_id, self.subject1.id)
        self.assertEqual(score.term_id, self.term1.id)


    def test_historical_class_results_remain_accessible_for_inactive_class(self):
        """Historical results should remain reportable after class deactivation."""
        self.grant(self.view_permission)

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.get(
            reverse("class_results"),
            {"class_id": self.class1.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.class1.name)

    def test_student_report_card_remains_accessible_after_class_deactivation(self):
        """A student's historical report card must remain accessible."""
        student_user = self.create_user(
            self.school1,
            "reportstudent",
            User.Role.STUDENT,
        )

        student = Student.objects.create(
            user=student_user,
            school_class=self.class1,
            admission_number="REPORT001",
        )

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "report_card",
                kwargs={
                    "student_id": student.id,
                    "term_id": self.term1.id,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        
    def test_inactive_class_allows_existing_allocation_submission(self):
        """An existing allocation can still be submitted after class deactivation."""
        self.grant(self.submit_permission)

        self.allocation.status = SubjectAllocation.Status.DRAFT
        self.allocation.save(update_fields=["status"])

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "submit_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.SUBMITTED,
        )


    def test_inactive_class_allows_existing_allocation_review(self):
        """A submitted allocation can still be reviewed after class deactivation."""
        self.grant(self.review_permission)

        self.allocation.status = SubjectAllocation.Status.SUBMITTED
        self.allocation.save(update_fields=["status"])

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "review_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.REVIEWED,
        )


    def test_inactive_class_allows_existing_allocation_approval(self):
        """A reviewed allocation can still be approved after class deactivation."""
        self.grant(self.approve_permission)

        self.allocation.status = SubjectAllocation.Status.REVIEWED
        self.allocation.save(update_fields=["status"])

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "approve_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.APPROVED,
        )


    def test_inactive_class_allows_existing_allocation_publication(self):
        """An approved allocation can still be published after class deactivation."""
        self.grant(self.publish_permission)

        self.allocation.status = SubjectAllocation.Status.APPROVED
        self.allocation.save(update_fields=["status"])

        self.class1.is_active = False
        self.class1.save(update_fields=["is_active"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "publish_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.PUBLISHED,
        )