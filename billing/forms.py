from django import forms

from .models import FeeStructure, Payment, OpeningBalance
from students.models import SchoolClass, Department, Student
from academics.models import Term


class OpeningBalanceForm(forms.ModelForm):

    class Meta:
        model = OpeningBalance
        fields = ['student', 'amount', 'note']

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated and not user.is_superuser:

            self.fields["student"].queryset = Student.objects.filter(
                user__school=user.school,
                is_active=True
            )


class FeeStructureForm(forms.ModelForm):

    class Meta:
        model = FeeStructure
        fields = [
            'school_class',
            'department',
            'term',
            'amount'
        ]

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user and user.is_authenticated and not user.is_superuser:

            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(
                    school=user.school
                )
            )

            self.fields["department"].queryset = (
                Department.objects.filter(
                    school=user.school
                )
            )

            self.fields["term"].queryset = (
                Term.objects.filter(
                    session__school=user.school
                )
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