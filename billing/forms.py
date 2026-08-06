from django import forms
from .models import FeeStructure, Payment
from .models import OpeningBalance

class OpeningBalanceForm(forms.ModelForm):
    class Meta:
        model = OpeningBalance
        fields = ['student', 'amount', 'note']

class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['school_class', 'department', 'term', 'amount']


class PaymentForm(forms.ModelForm):

    class Meta:

        model = Payment

        fields = [
            "amount",
            "payment_method",
            "reference",
            "note",
        ]