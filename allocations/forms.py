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


class BulkSubjectAllocationForm(forms.Form):
    """
    Professional bulk subject allocation.

    Select a class and term first.
    Subjects are then loaded from the subjects
    assigned to that class through ClassSubject.
    """

    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        empty_label="Select class",
    )

    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        empty_label="Select term",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        if not user or not user.school:
            return

        school = user.school

        self.fields['school_class'].queryset = (
            SchoolClass.objects.filter(
                school=school,
            )
            .order_by('name')
        )

        self.fields['term'].queryset = (
            Term.objects.filter(
                session__school=school,
            )
            .select_related('session')
            .order_by(
                '-session__name',
                'name',
            )
        )

    def get_teachers(self):
        """
        Return active teachers belonging to the user's school.
        """

        if not self.user or not self.user.school:
            return Teacher.objects.none()

        return (
            Teacher.objects.filter(
                user__school=self.user.school,
                is_active=True,
            )
            .select_related('user')
            .order_by(
                'user__last_name',
                'user__first_name',
                'user__other_name',
            )
        )

    def get_subjects(self):
        """
        Return active subjects assigned to the selected class.

        Subjects come from ClassSubject, not from the
        school's complete subject list.
        """

        if not self.user or not self.user.school:
            return Subject.objects.none()

        school_class = self.data.get('school_class')

        if not school_class:
            return Subject.objects.none()

        try:
            school_class = SchoolClass.objects.get(
                id=school_class,
                school=self.user.school,
            )
        except SchoolClass.DoesNotExist:
            return Subject.objects.none()

        from subjects.models import ClassSubject

        return (
            Subject.objects.filter(
                classsubject__school_class=school_class,
                school=self.user.school,
                is_active=True,
            )
            .distinct()
            .order_by('name')
        )

    def clean(self):
        cleaned_data = super().clean()

        school_class = cleaned_data.get('school_class')
        term = cleaned_data.get('term')

        if school_class and self.user and self.user.school:

            if school_class.school_id != self.user.school.id:
                raise forms.ValidationError(
                    "The selected class does not belong to your school."
                )

        if term and self.user and self.user.school:

            if term.session.school_id != self.user.school.id:
                raise forms.ValidationError(
                    "The selected term does not belong to your school."
                )

        return cleaned_data