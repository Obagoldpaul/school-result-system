from django.db import models


class FeeStructure(models.Model):
    school_class = models.ForeignKey('students.SchoolClass', on_delete=models.CASCADE)
    department = models.ForeignKey(
        'students.Department', on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="Leave blank for JSS classes. Set this for SSS classes where fees vary by department."
    )
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('school_class', 'department', 'term')

    def __str__(self):
        dept = f" ({self.department})" if self.department else ""
        return f"{self.school_class}{dept} - {self.term}: {self.amount}"


class Payment(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='payments')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateField(auto_now_add=True)
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=200, blank=True, help_text="e.g. bank transfer, cash, cheque number")

    def __str__(self):
        return f"{self.student} paid {self.amount} for {self.term}"

class OpeningBalance(models.Model):
    """One-time arrears a student owed BEFORE this system was used, entered manually during setup."""
    student = models.OneToOneField('students.Student', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=200, blank=True, help_text="e.g. 'Balance from 2025/2026 session'")

    def __str__(self):
        return f"{self.student} - Opening balance: {self.amount}"

def get_fee_for_student(student, term):
    """Finds the applicable fee amount for a student in a given term."""
    fee = FeeStructure.objects.filter(
        school_class=student.school_class,
        department=student.department,
        term=term
    ).first()
    if not fee and student.department is None:
        fee = FeeStructure.objects.filter(
            school_class=student.school_class,
            department__isnull=True,
            term=term
        ).first()
    return fee.amount if fee else None


def get_cumulative_balance(student, up_to_term):
    """
    Returns (total_fees_owed, total_paid, balance) — summing every term's fee
    up to and including up_to_term (within the same session), plus any
    opening balance, minus every payment the student has ever made.
    """
    from academics.models import Term

    def term_order(t):
        order_map = {'FIRST': 1, 'SECOND': 2, 'THIRD': 3}
        return order_map.get(t.name, 0)

    terms_in_session = Term.objects.filter(session=up_to_term.session)
    relevant_terms = [t for t in terms_in_session if term_order(t) <= term_order(up_to_term)]

    total_fees = 0
    for t in relevant_terms:
        fee = get_fee_for_student(student, t)
        if fee:
            total_fees += fee

    opening = OpeningBalance.objects.filter(student=student).first()
    if opening:
        total_fees += opening.amount

    total_paid = Payment.objects.filter(student=student).aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    return total_fees, total_paid, total_fees - total_paid

    