from decimal import Decimal

from django import forms
from django.forms import formset_factory
from django.db import models

from .models import (
    FeeCategory,
    FeeAssignment,
    Payment,
    OpeningBalance,
    PaymentAllocation,
    OpeningBalancePayment,
)

from students.models import SchoolClass, Department, Student
from academics.models import AcademicSession, Term

class FeeCategoryForm(forms.ModelForm):

    class Meta:
        model = FeeCategory
        fields = [
            "name",
            "category_type",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop(
            "user",
            None
        )

        super().__init__(
            *args,
            **kwargs
        )

    def save(self, commit=True):

        category = super().save(
            commit=False
        )

        # ---------------------------------------------------------
        # ASSIGN SCHOOL TO THE FEE CATEGORY
        # ---------------------------------------------------------

        if (
            self.user
            and self.user.is_authenticated
            and self.user.school_id
        ):

            category.school_id = self.user.school_id

        # ---------------------------------------------------------
        # SAVE
        # ---------------------------------------------------------

        if commit:
            category.save()

        return category

class OpeningBalanceForm(forms.ModelForm):

    class Meta:
        model = OpeningBalance
        fields = ['student', 'amount', 'note']
        widgets = {
            "student": forms.Select(attrs={"class": "form-select", "id": "opening-balance-student"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01", "placeholder": "0.00"}),
            "note": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Balance from 2025/2026 session"}),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated and not user.is_superuser:

            self.fields["student"].queryset = Student.objects.filter(
                user__school=user.school,
                is_active=True
            )

        self.fields["student"].label_from_instance = lambda student: (
            f"{student.admission_number} — "
            f"{student.user.get_full_name() or student.user.username} "
            f"({student.school_class})"
        )
        self.fields["student"].help_text = (
            "Search by admission number, student name, or class."
        )

class OpeningBalancePaymentForm(forms.ModelForm):

    class Meta:
        model = OpeningBalancePayment
        fields = [
            "amount",
            "payment_method",
            "reference",
            "note",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),

            "payment_method": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bank transaction ID, POS reference, etc.",
                }
            ),

            "note": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional payment note",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        opening_balance = kwargs.pop(
            "opening_balance",
            None
        )

        super().__init__(*args, **kwargs)

        self.opening_balance = opening_balance

        if opening_balance:

            total_paid = (
                opening_balance.payments.aggregate(
                    total=models.Sum("amount")
                )["total"]
                or Decimal("0.00")
            )

            self.total_paid = total_paid

            self.remaining_balance = (
                opening_balance.amount - total_paid
            )

        else:

            self.total_paid = Decimal("0.00")

            self.remaining_balance = Decimal("0.00")

    def clean_amount(self):

        amount = self.cleaned_data.get("amount")

        if amount is None:
            return amount

        if amount <= Decimal("0.00"):

            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        if self.opening_balance:

            if amount > self.remaining_balance:

                raise forms.ValidationError(
                    f"Payment cannot exceed the remaining "
                    f"opening balance of "
                    f"₦{self.remaining_balance:,.2f}."
                )

        return amount

class FeeAssignmentForm(forms.ModelForm):

    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        label="Academic Session",
        empty_label="Select academic session",
    )

    class Meta:
        model = FeeAssignment

        fields = [
            "fee_category",
            "session",
            "term",
            "school_class",
            "department",
            "student",
            "amount",
            "is_active",
        ]

        widgets = {
            # -------------------------------------------------
            # STUDENT IS NOT A DROPDOWN
            #
            # JavaScript will place the selected student ID
            # into this hidden field.
            # -------------------------------------------------
            "student": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        # =====================================================
        # EMPTY QUERYSETS BY DEFAULT
        # =====================================================

        self.fields["fee_category"].queryset = (
            FeeCategory.objects.none()
        )

        self.fields["session"].queryset = (
            AcademicSession.objects.none()
        )

        self.fields["term"].queryset = (
            Term.objects.none()
        )

        self.fields["school_class"].queryset = (
            SchoolClass.objects.none()
        )

        self.fields["department"].queryset = (
            Department.objects.none()
        )

        self.fields["student"].queryset = (
            Student.objects.none()
        )

        # =====================================================
        # USER MUST BE AUTHENTICATED
        # =====================================================

        if not user or not user.is_authenticated:
            return

        # =====================================================
        # SCHOOL-SCOPED QUERYSETS
        # =====================================================

        if user.is_superuser:

            self.fields["fee_category"].queryset = (
                FeeCategory.objects.filter(
                    is_active=True
                )
            )

            self.fields["session"].queryset = (
                AcademicSession.objects.all()
            )

            self.fields["school_class"].queryset = (
                SchoolClass.objects.all()
            )

            self.fields["department"].queryset = (
                Department.objects.all()
            )

            # IMPORTANT:
            # This queryset is NOT rendered as a dropdown.
            # The field uses HiddenInput.
            #
            # We keep the queryset so Django can validate
            # the selected student's ID.
            self.fields["student"].queryset = (
                Student.objects.filter(
                    is_active=True
                ).select_related(
                    "user",
                    "school_class",
                )
            )

        else:

            self.fields["fee_category"].queryset = (
                FeeCategory.objects.filter(
                    school=user.school,
                    is_active=True,
                )
            )

            self.fields["session"].queryset = (
                AcademicSession.objects.filter(
                    school=user.school,
                )
            )

            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(
                    school=user.school,
                )
            )

            self.fields["department"].queryset = (
                Department.objects.filter(
                    school=user.school,
                )
            )

            # IMPORTANT:
            # Keep this queryset for validation.
            # It will NOT appear as a dropdown.
            self.fields["student"].queryset = (
                Student.objects.filter(
                    user__school=user.school,
                    is_active=True,
                ).select_related(
                    "user",
                    "school_class",
                )
            )

        # =====================================================
        # DETERMINE SELECTED SESSION
        # =====================================================

        selected_session_id = None

        if self.is_bound:

            selected_session_id = self.data.get(
                "session"
            )

        elif self.instance and self.instance.pk:

            selected_session_id = (
                self.instance.term.session_id
            )

        # =====================================================
        # FILTER TERMS BY SESSION
        # =====================================================

        if selected_session_id:

            self.fields["term"].queryset = (
                Term.objects.filter(
                    session_id=selected_session_id
                )
            )

        # =====================================================
        # DETERMINE SELECTED CLASS
        # =====================================================

        selected_class_id = None

        if self.is_bound:

            selected_class_id = self.data.get(
                "school_class"
            )

        elif self.instance and self.instance.pk:

            selected_class_id = (
                self.instance.school_class_id
            )

        # =====================================================
        # FILTER STUDENTS BY CLASS
        #
        # Only narrow the validation queryset when a class
        # has actually been selected.
        # =====================================================

        if selected_class_id:

            self.fields["student"].queryset = (
                self.fields["student"].queryset.filter(
                    school_class_id=selected_class_id
                )
            )

        # =====================================================
        # DEPARTMENT
        #
        # Do NOT filter Department by school_class because
        # Department does not have a school_class field.
        #
        # School-level filtering was already done above.
        # =====================================================

        # =====================================================
        # OPTIONAL TARGET FIELDS
        # =====================================================

        self.fields["school_class"].required = False

        self.fields["department"].required = False

        self.fields["student"].required = False

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        cleaned_data = super().clean()

        fee_category = cleaned_data.get(
            "fee_category"
        )

        session = cleaned_data.get(
            "session"
        )

        term = cleaned_data.get(
            "term"
        )

        school_class = cleaned_data.get(
            "school_class"
        )

        department = cleaned_data.get(
            "department"
        )

        student = cleaned_data.get(
            "student"
        )

        # =====================================================
        # SESSION / TERM VALIDATION
        # =====================================================

        if session and term:

            if term.session_id != session.id:

                self.add_error(
                    "term",
                    "The selected term does not belong "
                    "to the selected academic session."
                )

        # =====================================================
        # TARGET VALIDATION
        # =====================================================

        if not student and not school_class:

            raise forms.ValidationError(
                "Select either a class or an individual student."
            )

        # =====================================================
        # INDIVIDUAL STUDENT CANNOT HAVE CLASS/DEPARTMENT
        # =====================================================

        if student:

            if school_class or department:

                raise forms.ValidationError(
                    "An individual student assignment cannot "
                    "also have a class or department."
                )

        # =====================================================
        # DEPARTMENT REQUIRES CLASS
        # =====================================================

        if department and not school_class:

            raise forms.ValidationError(
                "A department can only be selected together "
                "with a class."
            )

        # =====================================================
        # CLASS / DEPARTMENT CONSISTENCY
        # =====================================================

        if department and school_class:

            if department.school_id != school_class.school_id:

                raise forms.ValidationError(
                    "The selected department does not belong "
                    "to the selected school."
                )

        # =====================================================
        # STUDENT / CLASS CONSISTENCY
        # =====================================================

        if student and school_class:

            if student.school_class_id != school_class.id:

                raise forms.ValidationError(
                    "The selected student does not belong "
                    "to the selected class."
                )

        # =====================================================
        # FEE CATEGORY / SESSION SCHOOL CONSISTENCY
        # =====================================================

        if fee_category and session:

            if fee_category.school_id != session.school_id:

                raise forms.ValidationError(
                    "The selected fee category and academic "
                    "session must belong to the same school."
                )

        # =====================================================
        # TERM / SESSION CONSISTENCY
        # =====================================================

        if term and session:

            if term.session_id != session.id:

                self.add_error(
                    "term",
                    "The selected term does not belong "
                    "to the selected academic session."
                )

        return cleaned_data


FeeAssignmentFormSet = formset_factory(
    FeeAssignmentForm,
    extra=1,
    can_delete=True,
)

class PaymentForm(forms.ModelForm):

    class Meta:

        model = Payment

        fields = [
            "amount",
            "payment_method",
            "reference",
            "note",
        ]

        widgets = {
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Enter amount received",
            }),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Bank, POS, or cheque reference (optional)",
            }),
            "note": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Optional note for this payment",
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]

        if amount < Decimal("0.01"):
            raise forms.ValidationError(
                "Enter a payment amount greater than zero."
            )

        return amount

class StudentBillForm(forms.Form):

    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        label="Class",
        empty_label="Select class",
    )

    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        label="Student",
        empty_label="Select student",
    )

    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        label="Academic Session",
        empty_label="Select academic session",
    )

    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Term",
        empty_label="Select academic session first",
    )

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:

            # -------------------------------------------------
            # SCHOOL / SESSION / STUDENT ACCESS
            # -------------------------------------------------

            if user.is_superuser:

                self.fields["school_class"].queryset = (
                    SchoolClass.objects.all()
                )

                self.fields["session"].queryset = (
                    AcademicSession.objects.all()
                )

                students_queryset = Student.objects.filter(
                    is_active=True
                )

            else:

                self.fields["school_class"].queryset = (
                    SchoolClass.objects.filter(
                        school=user.school
                    )
                )

                self.fields["session"].queryset = (
                    AcademicSession.objects.filter(
                        school=user.school
                    )
                )

                students_queryset = Student.objects.filter(
                    user__school=user.school,
                    is_active=True
                )

            # -------------------------------------------------
            # FILTER STUDENTS BY SELECTED CLASS
            # -------------------------------------------------

            selected_class = None

            if self.is_bound:

                selected_class_id = self.data.get(
                    "school_class"
                )

                if selected_class_id:

                    try:

                        selected_class = SchoolClass.objects.get(
                            id=selected_class_id
                        )

                    except SchoolClass.DoesNotExist:

                        selected_class = None

            if selected_class:

                students_queryset = students_queryset.filter(
                    school_class=selected_class
                )

            self.fields["student"].queryset = students_queryset

            # -------------------------------------------------
            # FILTER TERMS BY SELECTED ACADEMIC SESSION
            # -------------------------------------------------

            selected_session = None

            if self.is_bound:

                selected_session_id = self.data.get(
                    "session"
                )

                if selected_session_id:

                    try:

                        if user.is_superuser:

                            selected_session = (
                                AcademicSession.objects.get(
                                    id=selected_session_id
                                )
                            )

                        else:

                            selected_session = (
                                AcademicSession.objects.get(
                                    id=selected_session_id,
                                    school=user.school
                                )
                            )

                    except AcademicSession.DoesNotExist:

                        selected_session = None

            if selected_session:

                self.fields["term"].queryset = (
                    Term.objects.filter(
                        session=selected_session
                    ).order_by("name")
                )

                # ---------------------------------------------
                # SHOW ONLY:
                # First Term
                # Second Term
                # Third Term
                #
                # Do NOT display the session beside the term.
                # ---------------------------------------------

                self.fields["term"].label_from_instance = (
                    lambda obj: obj.get_name_display()
                )

    # ---------------------------------------------------------
    # VALIDATE SESSION + TERM
    # ---------------------------------------------------------

    def clean(self):

        cleaned_data = super().clean()

        session = cleaned_data.get("session")
        term = cleaned_data.get("term")

        if (
            session
            and term
            and term.session_id != session.id
        ):

            self.add_error(
                "term",
                "The selected term does not belong to the selected academic session."
            )

        return cleaned_data

class PaymentAllocationForm(forms.ModelForm):

    class Meta:
        model = PaymentAllocation
        fields = [
            "fee_category",
            "amount",
            "note",
        ]

        widgets = {
            "fee_category": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={
                "class": "form-control allocation-amount",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "0.00",
            }),
            "note": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Optional allocation note",
            }),
        }

    def __init__(self, *args, **kwargs):

        fee_categories = kwargs.pop(
            "fee_categories",
            None
        )

        fee_breakdown = kwargs.pop(
            "fee_breakdown",
            None
        )

        super().__init__(*args, **kwargs)

        # An allocation row may be left unused.  The view ignores rows with
        # no amount, while completed rows are checked by clean_amount().
        self.fields["amount"].required = False

        if fee_categories is not None:

            self.fields["fee_category"].queryset = (
                fee_categories
            )

        # -------------------------------------------------
        # STORE OUTSTANDING BALANCES FOR THE TEMPLATE
        # -------------------------------------------------

        self.fee_balances = {}

        if fee_breakdown:

            for item in fee_breakdown:

                self.fee_balances[
                    item["fee_category"].id
                ] = item["balance"]
                
    def get_balance(self, category_id):

        return self.fee_balances.get(
            category_id,
            0
        )

    def get_balance_data(self):

        return {
            str(category_id): str(balance)
            for category_id, balance
            in self.fee_balances.items()
        }        

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        # Empty allocation rows are allowed; completed rows must be positive.
        if amount is not None and amount < Decimal("0.01"):
            raise forms.ValidationError(
                "Enter an allocation amount greater than zero."
            )

        return amount
        


PaymentAllocationFormSet = formset_factory(
    PaymentAllocationForm,
    extra=0,
    can_delete=True,
)
