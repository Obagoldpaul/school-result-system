from django import forms

from .models import SubjectAllocation
from teachers.models import Teacher
from subjects.models import Subject
from students.models import SchoolClass
from academics.models import Term


class SubjectAllocationForm(forms.ModelForm):

    class Meta:
        model = SubjectAllocation
        fields = [
            'teacher',
            'subject',
            'school_class',
            'term',
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and user.school:
            school = user.school

            self.fields['teacher'].queryset = Teacher.objects.filter(
                user__school=school,
                is_active=True,
            )

            self.fields['subject'].queryset = Subject.objects.filter(
                school=school,
                is_active=True,
            )

            self.fields['school_class'].queryset = SchoolClass.objects.filter(
                school=school,
            )

            self.fields['term'].queryset = Term.objects.filter(
                session__school=school,
            ).select_related(
                'session'
            ).order_by(
                '-session__name',
                'name',
            )

        else:
            self.fields['teacher'].queryset = Teacher.objects.none()
            self.fields['subject'].queryset = Subject.objects.none()
            self.fields['school_class'].queryset = SchoolClass.objects.none()
            self.fields['term'].queryset = Term.objects.none()