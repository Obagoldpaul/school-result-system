from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicSession, Term
from accounts.models import User
from billing.models import FeeAssignment, FeeCategory, Payment, PaymentAllocation
from schools.models import School, SchoolRole, Permission
from students.models import SchoolClass, Student
from datetime import date

from schools.models import (
    Feature,
    SubscriptionPackage,
    SchoolSubscription,
)

class BillingConsistencyTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="School One", code="SCH1")
        self.other_school = School.objects.create(name="School Two", code="SCH2")
        
        billing_feature = Feature.objects.create(
            code="BILLING",
            name="Billing",
            is_active=True,
        )

        self.package = SubscriptionPackage.objects.create(
            name=SubscriptionPackage.PackageType.STANDARD,
            description="Test package",
            price=Decimal("0.00"),
            is_active=True,
        )

        self.package.features.add(
            billing_feature
        )

        SchoolSubscription.objects.create(
            school=self.school,
            package=self.package,
            billing_cycle=SchoolSubscription.BillingCycle.TERMLY,
            start_date=date.today(),
            is_active=True,
        )
        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="Primary 1",
        )
        session = AcademicSession.objects.create(
            school=self.school,
            name="2026/2027",
            is_current=True,
        )
        self.term = Term.objects.create(
            session=session,
            name=Term.TermName.FIRST,
            is_current=True,
        )
        self.student_user = User.objects.create_user(
            username="student-one",
            school=self.school,
            role=User.Role.STUDENT,
        )
        self.student = Student.objects.create(
            user=self.student_user,
            school_class=self.school_class,
            admission_number="SCH1-001",
        )
        self.bursar = User.objects.create_user(
            username="bursar-one",
            school=self.school,
            role=User.Role.TEACHER,
        )
        
        billing_permissions = [
            {
                "code": "billing.view",
                "name": "View Billing",
            },
            {
                "code": "billing.manage",
                "name": "Manage Billing",
            },
            {
                "code": "billing.record_payment",
                "name": "Record Payments",
            },
            {
                "code": "billing.edit_payment",
                "name": "Edit Payments",
            },
            {
                "code": "billing.delete_payment",
                "name": "Delete Payments",
            },
            {
                "code": "billing.view_reports",
                "name": "View Billing Reports",
            },
        ]

        for permission_data in billing_permissions:
            Permission.objects.create(
                code=permission_data["code"],
                name=permission_data["name"],
                module="Billing",
                is_active=True,
            )


        self.bursar_role = SchoolRole.objects.create(
            school=self.school,
            name="Bursar",
        )

        self.bursar_role.permissions.set(
            Permission.objects.filter(
                code__in=[
                    "billing.view",
                    "billing.manage",
                    "billing.record_payment",
                    "billing.edit_payment",
                    "billing.delete_payment",
                    "billing.view_reports",
                ]
            )
        )

        self.bursar.school_role = self.bursar_role
        self.bursar.save(update_fields=["school_role"])
        
        self.category = FeeCategory.objects.create(
            school=self.school,
            name="Tuition",
        )
        FeeAssignment.objects.create(
            fee_category=self.category,
            term=self.term,
            school_class=self.school_class,
            amount=Decimal("100.00"),
        )
        self.client.force_login(self.bursar)

    def test_students_owing_matches_bill_when_a_legacy_payment_has_no_allocation(self):
        # This is the reported defect: a raw legacy payment made the old
        # cumulative list show no balance, although the bill still had no
        # category allocation and correctly showed a balance of 100.
        Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal("100.00"),
            recorded_by=self.bursar,
        )

        response = self.client.get(
            reverse("students_owing"),
            {"term": self.term.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.admission_number)
        self.assertEqual(response.context["rows"][0]["balance"], Decimal("100.00"))

    def test_duplicate_category_allocations_are_rejected_before_payment_is_created(self):
        response = self.client.post(
            reverse("record_payment", args=[self.student.id, self.term.id]),
            {
                "amount": "120.00",
                "payment_method": "Cash",
                "reference": "",
                "note": "",
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-fee_category": str(self.category.id),
                "form-0-amount": "60.00",
                "form-0-note": "",
                "form-1-fee_category": str(self.category.id),
                "form-1-amount": "60.00",
                "form-1-note": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tuition has only")
        self.assertEqual(Payment.objects.count(), 0)

    def test_record_payment_cannot_access_student_from_another_school(self):
        other_class = SchoolClass.objects.create(
            school=self.other_school,
            name="Primary 1",
        )
        other_user = User.objects.create_user(
            username="student-two",
            school=self.other_school,
            role=User.Role.STUDENT,
        )
        other_student = Student.objects.create(
            user=other_user,
            school_class=other_class,
            admission_number="SCH2-001",
        )

        response = self.client.get(
            reverse("record_payment", args=[other_student.id, self.term.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_account_statement_uses_allocations_and_shows_prior_session_arrears(self):
        prior_session = AcademicSession.objects.create(
            school=self.school,
            name="2025/2026",
        )
        prior_term = Term.objects.create(
            session=prior_session,
            name=Term.TermName.THIRD,
        )
        FeeAssignment.objects.create(
            fee_category=self.category,
            term=prior_term,
            school_class=self.school_class,
            amount=Decimal("80.00"),
        )
        payment = Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal("40.00"),
            recorded_by=self.bursar,
        )
        PaymentAllocation.objects.create(
            payment=payment,
            fee_category=self.category,
            amount=Decimal("40.00"),
        )
        # This legacy payment is deliberately not allocated and must not
        # reduce the current term's balance on the statement.
        Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal("60.00"),
            recorded_by=self.bursar,
        )

        response = self.client.get(
            reverse("student_account_statement", args=[self.student.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["term_arrears"], Decimal("140.00"))
        self.assertEqual(response.context["account_arrears"], Decimal("140.00"))
        self.assertContains(response, "2025/2026")
        self.assertContains(response, "140.00")

    def test_students_owing_includes_prior_term_arrears_after_selected_term_is_paid(self):
        prior_session = AcademicSession.objects.create(
            school=self.school,
            name="2025/2026",
        )
        prior_term = Term.objects.create(session=prior_session, name=Term.TermName.THIRD)
        FeeAssignment.objects.create(
            fee_category=self.category,
            term=prior_term,
            school_class=self.school_class,
            amount=Decimal("80.00"),
        )
        payment = Payment.objects.create(
            student=self.student,
            term=self.term,
            amount=Decimal("100.00"),
            recorded_by=self.bursar,
        )
        PaymentAllocation.objects.create(
            payment=payment,
            fee_category=self.category,
            amount=Decimal("100.00"),
        )

        response = self.client.get(reverse("students_owing"), {"term": self.term.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), 1)
        row = response.context["rows"][0]
        self.assertEqual(row["balance"], Decimal("0.00"))
        self.assertEqual(row["account_arrears"], Decimal("80.00"))
        self.assertEqual(row["outstanding_terms"][0]["term"], prior_term)
