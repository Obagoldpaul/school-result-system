from django import forms
from .models import SubjectAllocation


class SubjectAllocationForm(forms.ModelForm):
    class Meta:
        model = SubjectAllocation
        fields = ['teacher', 'subject', 'school_class', 'term']