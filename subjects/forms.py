from django import forms
from .models import Subject, ClassSubject


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'parent']


class ClassSubjectForm(forms.ModelForm):
    class Meta:
        model = ClassSubject
        fields = ['school_class', 'subject']