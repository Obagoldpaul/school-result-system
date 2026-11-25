from django.test import TestCase
from django.urls import reverse
from students.models import Student, Department
from .services import get_students_for_allocation
from .models import Score
from academics.models import SchoolSettings
from datetime import date

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
from subjects.models import Subject, ClassSubject
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
        
        self.package = SubscriptionPackage.objects.get(
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

    def test_allocation_selector_uses_actual_academic_chronology(self):
        self.grant(self.view_permission)
        self.client.force_login(self.user)

        # Session names deliberately conflict with their actual dates.
        earlier_session = AcademicSession.objects.create(
            school=self.school1,
            name="2028/2029",
        )

        later_session = AcademicSession.objects.create(
            school=self.school1,
            name="2024/2025",
        )

        earlier_term = Term.objects.create(
            session=earlier_session,
            name=Term.TermName.SECOND,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        later_term = Term.objects.create(
            session=later_session,
            name=Term.TermName.FIRST,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
        )

        # Create a term belonging to another school.
        foreign_session = AcademicSession.objects.create(
            school=self.school2,
            name="2023/2024",
        )

        foreign_term = Term.objects.create(
            session=foreign_session,
            name=Term.TermName.FIRST,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 31),
        )

        response = self.client.get(
            reverse("select_allocation")
        )

        self.assertEqual(response.status_code, 200)

        # Terms should follow actual dates, with undated legacy
        # terms placed after completely dated terms.
        self.assertEqual(
            list(response.context["terms"]),
            [earlier_term, later_term, self.term1],
        )

        # Sessions should follow their earliest complete term dates.
        self.assertEqual(
            list(response.context["sessions"]),
            [
                earlier_session,
                later_session,
                self.term1.session,
            ],
        )

        # Another school's term must never appear.
        self.assertNotIn(
            foreign_term,
            response.context["terms"],
        )
    
    def test_management_can_return_reviewed_allocation_for_correction(self):
        self.grant(self.approve_permission)

        student_user = self.create_user(
            self.school1,
            "returnteststudent",
            User.Role.STUDENT,
        )

        student = Student.objects.create(
            user=student_user,
            school_class=self.class1,
            admission_number="RETURN001",
        )

        score = Score.objects.create(
            student=student,
            subject=self.subject1,
            term=self.term1,
            ca_score=30,
            exam_score=50,
            recorded_by=self.teacher1,
        )

        self.allocation.status = SubjectAllocation.Status.REVIEWED
        self.allocation.class_teacher_comment = "Please review these scores."
        self.allocation.save(
            update_fields=["status", "class_teacher_comment"]
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "return_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 302)

        self.allocation.refresh_from_db()
        score.refresh_from_db()

        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.DRAFT,
        )
        self.assertEqual(
            self.allocation.class_teacher_comment,
            "Please review these scores.",
        )
        self.assertEqual(score.ca_score, 30)
        self.assertEqual(score.exam_score, 50)
    
    
    def test_return_allocation_denied_without_approval_permission(self):
        self.allocation.status = SubjectAllocation.Status.REVIEWED
        self.allocation.save(update_fields=["status"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "return_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 403)
        
    def test_return_allocation_denies_cross_school_access(self):
        self.grant(self.approve_permission)

        teacher2 = self.create_teacher(
            self.school2,
            "returnteacher2",
            "RETURN-T002",
        )
        class2 = self.create_class(self.school2, "Primary 1")
        subject2 = self.create_subject(
            self.school2,
            "Mathematics",
            "RETURN-M002",
        )
        term2 = self.create_term(self.school2)

        other_allocation = SubjectAllocation.objects.create(
            teacher=teacher2,
            subject=subject2,
            school_class=class2,
            term=term2,
            status=SubjectAllocation.Status.REVIEWED,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "return_allocation",
                kwargs={"allocation_id": other_allocation.id},
            )
        )

        self.assertEqual(response.status_code, 404)
        
    
    def test_return_allocation_rejects_unreviewed_allocation(self):
        self.grant(self.approve_permission)

        self.allocation.status = SubjectAllocation.Status.DRAFT
        self.allocation.save(update_fields=["status"])

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "return_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 403)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.DRAFT,
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

    def test_teacher_cannot_return_allocation_even_with_approval_permission(self):
        self.grant(self.approve_permission)

        teacher_user = self.teacher1.user
        teacher_user.school_role = self.role
        teacher_user.save(update_fields=["school_role"])

        self.allocation.status = SubjectAllocation.Status.REVIEWED
        self.allocation.save(update_fields=["status"])

        self.client.force_login(teacher_user)

        response = self.client.post(
            reverse(
                "return_allocation",
                kwargs={"allocation_id": self.allocation.id},
            )
        )

        self.assertEqual(response.status_code, 403)

        self.allocation.refresh_from_db()
        self.assertEqual(
            self.allocation.status,
            SubjectAllocation.Status.REVIEWED,
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
        
    def test_student_report_term_selector_uses_actual_academic_chronology(self):
        student_user = self.create_user(
            self.school1,
            "chronologystudent",
            User.Role.STUDENT,
        )

        student = Student.objects.create(
            user=student_user,
            school_class=self.class1,
            admission_number="CHRON001",
        )

        # Session names deliberately conflict with actual dates.
        earlier_session = AcademicSession.objects.create(
            school=self.school1,
            name="2028/2029",
        )

        later_session = AcademicSession.objects.create(
            school=self.school1,
            name="2024/2025",
        )

        earlier_term = Term.objects.create(
            session=earlier_session,
            name=Term.TermName.SECOND,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        later_term = Term.objects.create(
            session=later_session,
            name=Term.TermName.FIRST,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
        )

        foreign_session = AcademicSession.objects.create(
            school=self.school2,
            name="2023/2024",
        )

        foreign_term = Term.objects.create(
            session=foreign_session,
            name=Term.TermName.FIRST,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 31),
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "select_report_term",
                kwargs={"student_id": student.id},
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list(response.context["terms"]),
            [earlier_term, later_term, self.term1],
        )

        self.assertNotIn(
            foreign_term,
            response.context["terms"],
        )
    
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
        
    
        
class ScoreEntryEligibilityTests(ScorePermissionTestMixin, TestCase):

    def setUp(self):
        self.school = self.create_school(
            "Eligibility Test School",
            "ELIG001",
        )

        self.teacher = self.create_teacher(
            self.school,
            "eligibility_teacher",
            "ELIG-T001",
        )

        self.school_class = self.create_class(
            self.school,
            "Primary 1",
        )

        self.term = self.create_term(self.school)

        self.department_a = Department.objects.create(
            school=self.school,
            name="Department A",
        )

        self.department_b = Department.objects.create(
            school=self.school,
            name="Department B",
        )

        self.student_a = self.create_student(
            "eligibility_student_a",
            "ELIG-ST001",
            department=self.department_a,
        )

        self.student_b = self.create_student(
            "eligibility_student_b",
            "ELIG-ST002",
            department=self.department_b,
        )

        self.student_without_department = self.create_student(
            "eligibility_student_c",
            "ELIG-ST003",
        )

    def create_student(
        self,
        username,
        admission_number,
        department=None,
    ):
        user = self.create_user(
            self.school,
            username,
            User.Role.STUDENT,
        )

        return Student.objects.create(
            user=user,
            school_class=self.school_class,
            department=department,
            admission_number=admission_number,
        )

    def create_primary_subject(
        self,
        name,
        code,
        is_elective=False,
    ):
        return Subject.objects.create(
            school=self.school,
            level=Subject.SubjectLevel.PRIMARY,
            name=name,
            code=code,
            is_elective=is_elective,
        )

    def create_allocation(self, subject):
        return SubjectAllocation.objects.create(
            teacher=self.teacher,
            subject=subject,
            school_class=self.school_class,
            term=self.term,
        )

    def test_compulsory_subject_is_available_to_all_class_students(self):
        subject = self.create_primary_subject(
            "Compulsory English",
            "ELIG-ENG",
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=subject,
        )
        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertSetEqual(
            set(students),
            {
                self.student_a,
                self.student_b,
                self.student_without_department,
            },
        )

    def test_unselected_elective_is_excluded(self):
        subject = self.create_primary_subject(
            "Elective Subject A",
            "ELIG-EA",
            is_elective=True,
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=subject,
        )
        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertFalse(students.exists())

    def test_selected_elective_is_included(self):
        subject = self.create_primary_subject(
            "Elective Subject B",
            "ELIG-EB",
            is_elective=True,
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=subject,
        )
        self.student_a.elective_subjects.add(subject)
        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertSetEqual(
            set(students),
            {self.student_a},
        )

    def test_class_subject_assignment_does_not_restrict_students(self):
        subject = self.create_primary_subject(
            "Department A Subject",
            "ELIG-DA",
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=subject,
        )
        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertSetEqual(
            set(students),
            {
                self.student_a,
                self.student_b,
                self.student_without_department,
            },
        )

    def test_subject_not_assigned_to_class_is_excluded(self):
        subject = self.create_primary_subject(
            "Unassigned Subject",
            "ELIG-UN",
        )
        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertFalse(students.exists())

    def test_inactive_students_are_excluded(self):
        subject = self.create_primary_subject(
            "Active Class Subject",
            "ELIG-ACT",
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=subject,
        )

        self.student_a.is_active = False
        self.student_a.save(update_fields=["is_active"])

        allocation = self.create_allocation(subject)

        students = get_students_for_allocation(allocation)

        self.assertNotIn(self.student_a, students)
        self.assertIn(self.student_b, students)

    
class ReportCardCalculationTests(ScorePermissionTestMixin, TestCase):
    def setUp(self):
        self.school = self.create_school(
            name="Report Test School",
            code="RPTS",
        )
        self.school_class = self.create_class(
            self.school,
            "Primary 1",
        )

        student_user = self.create_user(
            self.school,
            "report_test_student",
            role=User.Role.STUDENT,
        )
        self.student = Student.objects.create(
            user=student_user,
            school_class=self.school_class,
            admission_number="RPT-001",
        )
        
        self.teacher = self.create_teacher(
            self.school,
            "report_test_teacher",
            "RPT-T001",
        )

        self.session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
        )
        self.first_term = Term.objects.create(
            session=self.session,
            name=Term.TermName.FIRST,
        )
        self.second_term = Term.objects.create(
            session=self.session,
            name=Term.TermName.SECOND,
        )

        self.parent_subject = self.create_subject(
            self.school,
            "Basic Science",
            "BS",
        )
        self.child_one = Subject.objects.create(
            school=self.school,
            name="Basic Science - Biology",
            code="BS-BIO",
            parent=self.parent_subject,
        )
        self.child_two = Subject.objects.create(
            school=self.school,
            name="Basic Science - Chemistry",
            code="BS-CHEM",
            parent=self.parent_subject,
        )
        self.maths = self.create_subject(
            self.school,
            "Mathematics",
            "MATH",
        )

    def add_score(self, subject, term, ca_score, exam_score):
        return Score.objects.create(
            student=self.student,
            subject=subject,
            term=term,
            ca_score=ca_score,
            exam_score=exam_score,
            recorded_by=self.teacher,
        )

    def test_report_card_combines_child_subjects_into_one_parent_row(self):
        self.add_score(self.child_one, self.first_term, 10, 40)
        self.add_score(self.child_two, self.first_term, 20, 60)

        from scores.reports import get_report_card_rows

        rows = get_report_card_rows(self.student, self.first_term)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subject_name"], "Basic Science")
        self.assertEqual(rows[0]["ca_score"], 15)
        self.assertEqual(rows[0]["exam_score"], 50)
        self.assertEqual(rows[0]["total_score"], 65)

    def test_cumulative_rows_average_available_term_scores_per_subject(self):
        # Basic Science: two child subjects combined in each term.
        self.add_score(self.child_one, self.first_term, 10, 40)
        self.add_score(self.child_two, self.first_term, 20, 60)
        self.add_score(self.child_one, self.second_term, 20, 50)
        self.add_score(self.child_two, self.second_term, 30, 60)

        # Mathematics has a score only in First Term.
        self.add_score(self.maths, self.first_term, 20, 60)

        from scores.reports import get_cumulative_report_rows

        rows, relevant_terms = get_cumulative_report_rows(
            self.student,
            self.second_term,
        )

        rows_by_name = {
            row["subject_name"]: row
            for row in rows
        }

        self.assertEqual(
            [term.id for term in relevant_terms],
            [self.first_term.id, self.second_term.id],
        )
        self.assertEqual(
            rows_by_name["Basic Science"]["average"],
            72.5,
        )
        self.assertEqual(
            rows_by_name["Mathematics"]["average"],
            80,
        )
        self.assertEqual(
            rows_by_name["Mathematics"]["term_scores"],
            [80, None],
        )