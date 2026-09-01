from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from academics.utils import get_term_order
import datetime
from django.db.models import Q, Sum

class FeeCategory(models.Model):
    """
    A customizable type of fee used by a particular school.

    Each school can create, rename, activate/deactivate, and manage
    its own fee categories.
    """

    CATEGORY_TYPES = [
        ("COMPULSORY", "Compulsory"),
        ("OPTIONAL", "Optional"),
    ]

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="fee_categories",
    )

    name = models.CharField(
        max_length=100,
        help_text="e.g. Tuition, WAEC Fee, Graduation Party, Transport."
    )

    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        default="COMPULSORY",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_fee_category_per_school",
            )
        ]

    def __str__(self):
        return self.name


class FeeAssignment(models.Model):
    """
    Assigns a fee category and amount to a class, department,
    or individual student for a particular term.

    This allows schools to have flexible compulsory and optional
    charges without forcing every student to pay optional fees.
    """

    fee_category = models.ForeignKey(
        FeeCategory,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.CASCADE,
        related_name="fee_assignments",
    )

    school_class = models.ForeignKey(
        "students.SchoolClass",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_assignments",
    )

    department = models.ForeignKey(
        "students.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_assignments",
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_assignments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    
    def clean(self):
        """
        Validate the fee assignment target.

        Valid targets:
        1. Class-wide
        2. Class + Department
        3. Individual student
        """

        if self.student_id:
            # Individual student assignment.
            # A student assignment must not also specify
            # a class or department.
            if self.school_class_id or self.department_id:
                raise ValidationError(
                    "An individual student fee assignment cannot "
                    "also have a class or department."
                )

            return

        # If there is no individual student, a class is required.
        if not self.school_class_id:
            raise ValidationError(
                "A fee assignment must target a class "
                "or an individual student."
            )

        # Department is optional.
        # Therefore:
        #
        # Class
        # OR
        # Class + Department
        #
        # are both valid.

    class Meta:
        ordering = ["fee_category__name", "term"]

    def __str__(self):
        return f"{self.fee_category} - {self.amount}"

class OptionalFeeEnrollment(models.Model):
    """
    Records whether a student has opted into an optional fee assignment.

    Optional fees are NOT automatically billed simply because the
    fee assignment applies to the student's class/department.

    A student must have an active enrollment record before the
    optional fee appears on the student's bill.
    """

    fee_assignment = models.ForeignKey(
        FeeAssignment,
        on_delete=models.CASCADE,
        related_name="optional_enrollments",
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="optional_fee_enrollments",
    )

    opted_in = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fee_assignment", "student"],
                name="unique_optional_fee_enrollment",
            )
        ]
        ordering = ["student"]

    def __str__(self):
        status = "Opted In" if self.opted_in else "Opted Out"

        return (
            f"{self.student} - "
            f"{self.fee_assignment.fee_category} - "
            f"{status}"
        )

def get_fee_assignments_for_student(student, term):
    """
    Returns the active fee assignments applicable to a student
    for a particular term.

    Compulsory fees:
        Automatically included when the assignment applies.

    Optional fees:
        Included only when the student has explicitly opted in
        through OptionalFeeEnrollment.

    Priority:
        1. Individual student assignment
        2. Department assignment
        3. Class assignment

    A more specific assignment overrides a broader assignment
    for the same fee category.
    """

    assignments = (
        FeeAssignment.objects
        .filter(
            term=term,
            is_active=True,
            fee_category__school=student.user.school,
        )
        .select_related(
            "fee_category",
            "school_class",
            "department",
            "student",
        )
    )

    applicable = {}

    for assignment in assignments:

        # -------------------------------------------------
        # OPTIONAL FEE CHECK
        # -------------------------------------------------
        #
        # Optional fees should NOT automatically appear
        # on every applicable student's bill.
        #
        # They must have an active enrollment record.
        #

        if assignment.fee_category.category_type == "OPTIONAL":

            opted_in = OptionalFeeEnrollment.objects.filter(
                fee_assignment=assignment,
                student=student,
                opted_in=True,
            ).exists()

            if not opted_in:
                continue

        # -------------------------------------------------
        # INDIVIDUAL STUDENT ASSIGNMENT
        # -------------------------------------------------

        if assignment.student_id == student.id:

            applicable[assignment.fee_category_id] = assignment

            continue

        # -------------------------------------------------
        # DEPARTMENT ASSIGNMENT
        # -------------------------------------------------

        if (
            assignment.department_id
            and assignment.department_id == student.department_id
        ):

            if assignment.fee_category_id not in applicable:

                applicable[assignment.fee_category_id] = assignment

            continue

        # -------------------------------------------------
        # CLASS ASSIGNMENT
        # -------------------------------------------------

        if (
            assignment.school_class_id
            and assignment.school_class_id == student.school_class_id
        ):

            if assignment.fee_category_id not in applicable:

                applicable[assignment.fee_category_id] = assignment

    return list(applicable.values())

class Payment(models.Model):

    PAYMENT_METHODS = [
        ("Cash", "Cash"),
        ("Bank Transfer", "Bank Transfer"),
        ("POS", "POS"),
        ("Cheque", "Cheque"),
        ("Online", "Online"),
    ]

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='payments'
    )

    term = models.ForeignKey(
        'academics.Term',
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="Cash",
    )

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank transaction ID, POS reference, cheque number, etc."
    )

    date_paid = models.DateField(
        auto_now_add=True
    )

    recorded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )

    note = models.CharField(
        max_length=200,
        blank=True,
        help_text="Additional payment note"
    )

    def __str__(self):
        return f"{self.student} paid ₦{self.amount}"

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.receipt_number:

            self.receipt_number = (
                f"REC-{self.date_paid.strftime('%Y%m%d')}-{self.id:05d}"
            )

            super().save(update_fields=["receipt_number"])
    
    class Meta:
        permissions = [
            (
                "record_payment",
                "Can record student payments",
            ),
            (
                "edit_payment",
                "Can edit student payments",
            ),
            (
                "view_payment_history",
                "Can view student payment history",
            ),
            (
                "view_student_owing",
                "Can view students owing fees",
            ),
        ]

class PaymentAllocation(models.Model):
    """
    Shows exactly what a payment was used to pay for.

    A payment can be allocated either to:
        1. A normal fee category
        2. The student's opening balance

    One Payment can therefore be divided across multiple
    fee categories and/or the opening balance.
    """

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    fee_category = models.ForeignKey(
        FeeCategory,
        on_delete=models.PROTECT,
        related_name="payment_allocations",
        null=True,
        blank=True,
    )

    opening_balance = models.ForeignKey(
        "OpeningBalance",
        on_delete=models.PROTECT,
        related_name="payment_allocations",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    note = models.CharField(
        max_length=200,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["fee_category__name", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["payment", "fee_category"],
                name="unique_payment_fee_category",
            ),

            models.UniqueConstraint(
                fields=["payment", "opening_balance"],
                name="unique_payment_opening_balance",
            ),
        ]

    def __str__(self):

        if self.opening_balance:

            destination = "Opening Balance"

        elif self.fee_category:

            destination = str(self.fee_category)

        else:

            destination = "Unassigned"

        return (
            f"{self.payment.receipt_number} - "
            f"{destination}: ₦{self.amount}"
        )
        
def get_student_fee_breakdown(student, term):
    """
    Returns the fee breakdown for a student for a particular term.

    Each item contains:
        - fee category
        - category type
        - assigned amount
        - amount paid
        - balance
        - payment status
    """

    assignments = get_fee_assignments_for_student(
        student,
        term
    )

    breakdown = []

    for assignment in assignments:

        paid = PaymentAllocation.objects.filter(
            payment__student=student,
            payment__term=term,
            fee_category=assignment.fee_category,
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or 0

        balance = assignment.amount - paid

        if paid >= assignment.amount:
            status = "Paid"

        elif paid > 0:
            status = "Part Payment"

        else:
            status = "Owing"

        breakdown.append({
            "assignment": assignment,
            "fee_category": assignment.fee_category,
            "category_type": assignment.fee_category.category_type,
            "amount": assignment.amount,
            "paid": paid,
            "balance": max(balance, 0),
            "status": status,
        })

    return breakdown

def get_current_term_billing_summary(students, term):
    """
    Calculate current-term billing totals for a set of students.

    Uses get_student_fee_breakdown() as the authoritative source
    for each student's current-term charges, payments and balance.

    Opening balances are intentionally excluded.
    """

    total_collected = (
        Payment.objects
        .filter(
            student__in=students,
            term=term,
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    students_owing = 0
    outstanding = Decimal("0.00")

    for student in students:

        breakdown = get_student_fee_breakdown(
            student,
            term,
        )

        balance = sum(
            (
                item["balance"]
                for item in breakdown
            ),
            Decimal("0.00"),
        )

        if balance > 0:
            students_owing += 1
            outstanding += balance

    expected_revenue = Decimal("0.00")

    for student in students:

        breakdown = get_student_fee_breakdown(
            student,
            term,
        )

        expected_revenue += sum(
            (
                item["amount"]
                for item in breakdown
            ),
            Decimal("0.00"),
        )

    collection_rate = (
        (
            total_collected
            / expected_revenue
        ) * 100
        if expected_revenue > 0
        else 0
    )

    return {
        "total_collected": total_collected,
        "students_owing": students_owing,
        "outstanding": outstanding,
        "expected_revenue": expected_revenue,
        "collection_rate": round(
            collection_rate,
            2,
        ),
    }

def get_student_account_summary(student):
    """
    Returns the student's complete account position
    across all academic sessions.

    Payments are counted through PaymentAllocation so that
    unallocated/legacy payments do not incorrectly reduce
    outstanding fee balances.
    """

    from academics.models import AcademicSession

    sessions = (
        AcademicSession.objects
        .filter(
            school=student.user.school,
        )
        .prefetch_related("terms")
        .order_by("id")
    )

    statement_sessions = []

    total_charged = Decimal("0.00")
    total_allocated = Decimal("0.00")

    for session in sessions:

        term_rows = []

        for term in sorted(
            session.terms.all(),
            key=get_term_order,
        ):

            breakdown = get_student_fee_breakdown(
                student,
                term,
            )

            charged = sum(
                (
                    item["amount"]
                    for item in breakdown
                ),
                Decimal("0.00"),
            )

            allocated = sum(
                (
                    item["paid"]
                    for item in breakdown
                ),
                Decimal("0.00"),
            )

            balance = sum(
                (
                    item["balance"]
                    for item in breakdown
                ),
                Decimal("0.00"),
            )

            allocation_exists = PaymentAllocation.objects.filter(
                payment__student=student,
                payment__term=term,
            ).exists()

            if charged or allocated or allocation_exists:

                term_rows.append({
                    "term": term,
                    "charged": charged,
                    "allocated": allocated,
                    "balance": balance,
                    "breakdown": breakdown,
                })

                total_charged += charged
                total_allocated += allocated

        if term_rows:

            statement_sessions.append({
                "session": session,
                "terms": term_rows,
                "charged": sum(
                    (
                        row["charged"]
                        for row in term_rows
                    ),
                    Decimal("0.00"),
                ),
                "allocated": sum(
                    (
                        row["allocated"]
                        for row in term_rows
                    ),
                    Decimal("0.00"),
                ),
                "arrears": sum(
                    (
                        row["balance"]
                        for row in term_rows
                    ),
                    Decimal("0.00"),
                ),
            })

    # ---------------------------------------------------------
    # OPENING BALANCE
    # ---------------------------------------------------------

    opening_balance = (
        OpeningBalance.objects
        .filter(student=student)
        .first()
    )

    if opening_balance:

        opening_balance_paid = (
            opening_balance.payments.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        opening_arrears = (
            opening_balance.amount
            - opening_balance_paid
        )

        # Never allow the balance to become negative.
        if opening_arrears < Decimal("0.00"):
            opening_arrears = Decimal("0.00")

    else:

        opening_balance_paid = Decimal("0.00")

        opening_arrears = Decimal("0.00")

    # ---------------------------------------------------------
    # TERM ARREARS
    # ---------------------------------------------------------

    term_arrears = sum(
        (
            session_row["arrears"]
            for session_row in statement_sessions
        ),
        Decimal("0.00"),
    )

    # ---------------------------------------------------------
    # TOTAL ACCOUNT ARREARS
    # ---------------------------------------------------------

    account_arrears = (
        term_arrears
        + opening_arrears
    )

    return {
        "statement_sessions": statement_sessions,
        "total_charged": total_charged,
        "total_allocated": total_allocated,
        "term_arrears": term_arrears,
        "opening_balance": opening_balance,
        "opening_arrears": opening_arrears,
        "account_arrears": account_arrears,
    }

class OpeningBalance(models.Model):
    """One-time arrears a student owed BEFORE this system was used, entered manually during setup."""
    student = models.OneToOneField('students.Student', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=200, blank=True, help_text="e.g. 'Balance from 2025/2026 session'")

    def __str__(self):
        return f"{self.student} - Opening balance: {self.amount}"
    
class OpeningBalancePayment(models.Model):
    """
    Payment made specifically toward a student's opening balance.

    Opening balance payments are kept separate from normal term-fee
    PaymentAllocation records because the opening balance represents
    arrears that existed before the billing system was introduced.
    """

    PAYMENT_METHODS = [
        ("Cash", "Cash"),
        ("Bank Transfer", "Bank Transfer"),
        ("POS", "POS"),
        ("Cheque", "Cheque"),
        ("Online", "Online"),
    ]

    opening_balance = models.ForeignKey(
        OpeningBalance,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="Cash",
    )

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank transaction ID, POS reference, cheque number, etc.",
    )

    date_paid = models.DateField(
        auto_now_add=True,
    )

    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )

    note = models.CharField(
        max_length=200,
        blank=True,
        help_text="Additional payment note",
    )

    def __str__(self):
        return (
            f"{self.opening_balance.student} "
            f"paid ₦{self.amount:,.2f} "
            f"toward opening balance"
        )

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.receipt_number:

            self.receipt_number = (
                f"OB-REC-{self.date_paid.strftime('%Y%m%d')}-"
                f"{self.id:05d}"
            )

            super().save(
                update_fields=["receipt_number"]
            )

def get_opening_balance_paid(student):
    """
    Returns the total amount paid toward a student's opening balance.
    """

    opening = OpeningBalance.objects.filter(
        student=student
    ).first()

    if not opening:
        return Decimal("0.00")

    return OpeningBalancePayment.objects.filter(
        opening_balance=opening
    ).aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0.00")


def get_opening_balance_arrears(student):
    """
    Returns the remaining unpaid opening balance.
    """

    opening = OpeningBalance.objects.filter(
        student=student
    ).first()

    if not opening:
        return Decimal("0.00")

    paid = OpeningBalancePayment.objects.filter(
        opening_balance=opening
    ).aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0.00")

    return max(
        opening.amount - paid,
        Decimal("0.00"),
    )


def get_fee_for_student(student, term):
    """
    Returns the total applicable fee amount for a student
    for a particular term using the new FeeAssignment system.

    Compulsory fees are automatically included.

    Optional fees are included only when the student has
    explicitly opted in.
    """

    assignments = get_fee_assignments_for_student(
        student,
        term,
    )

    return sum(
        assignment.amount
        for assignment in assignments
    )


def get_cumulative_balance(student, up_to_term):
    """
    Returns:

        (total_fees_owed, total_paid, balance)

    for all applicable fee assignments from the beginning
    of the selected term's session up to and including
    `up_to_term`.

    OpeningBalance is included.

    Payments are counted only up to the selected term.

    This uses the new fee-category / FeeAssignment billing
    system rather than the old FeeStructure calculation.
    """

    from academics.models import Term

    # ---------------------------------------------------------
    # GET TERMS IN THE SAME SESSION
    # ---------------------------------------------------------

    terms_in_session = Term.objects.filter(
        session=up_to_term.session
    )

    relevant_terms = [
        term
        for term in terms_in_session
        if get_term_order(term) <= get_term_order(up_to_term)
    ]

    # ---------------------------------------------------------
    # TOTAL FEES FROM FEE ASSIGNMENTS
    # ---------------------------------------------------------

    total_fees = 0

    for term in relevant_terms:

        fee_breakdown = get_student_fee_breakdown(
            student,
            term
        )

        total_fees += sum(
            item["amount"]
            for item in fee_breakdown
        )

        # ---------------------------------------------------------
        # OPENING BALANCE
        # ---------------------------------------------------------

        opening = OpeningBalance.objects.filter(
            student=student
        ).first()

        opening_amount = (
            opening.amount
            if opening
            else Decimal("0.00")
        )

        opening_paid = Decimal("0.00")

        if opening:

            opening_paid = (
                OpeningBalancePayment.objects.filter(
                    opening_balance=opening
                ).aggregate(
                    total=models.Sum("amount")
                )["total"]
                or Decimal("0.00")
            )

        opening_arrears = max(
            opening_amount - opening_paid,
            Decimal("0.00"),
        )

        # ---------------------------------------------------------
        # TOTAL PAYMENTS UP TO SELECTED TERM
        # ---------------------------------------------------------

        term_payments = Payment.objects.filter(
            student=student,
            term__in=relevant_terms,
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

        # ---------------------------------------------------------
        # TOTAL PAID
        # ---------------------------------------------------------

        total_paid = (
            opening_paid +
            term_payments
        )

        # ---------------------------------------------------------
        # BALANCE
        # ---------------------------------------------------------

        balance = (
            total_fees
            - total_paid
        )

        return (
            total_fees,
            total_paid,
            balance,
        )