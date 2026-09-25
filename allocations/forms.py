from django import forms

from .models import SubjectAllocation
from teachers.models import Teacher
from subjects.models import Subject
from students.models import SchoolClass
from academics.models import AcademicSession, Term


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
                is_active=True,
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
                is_active=True,
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
    
class CarryForwardAllocationForm(forms.Form):
    """
    Select source and destination academic sessions and terms for
    carrying subject allocations forward.
    """

    from_session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        empty_label="Select source session",
    )

    from_term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        empty_label="Select source term",
    )

    to_session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        empty_label="Select destination session",
    )

    to_term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        empty_label="Select destination term",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        if not user or not user.school:
            return

        school = user.school

        sessions = (
            AcademicSession.objects.filter(
                school=school,
            )
            .order_by("-name")
        )

        terms = (
            Term.objects.filter(
                session__school=school,
            )
            .select_related("session")
            .order_by(
                "-session__name",
                "name",
            )
        )

        self.fields["from_session"].queryset = sessions
        self.fields["to_session"].queryset = sessions
        
        self.school_terms = terms

        current_term = (
            terms.filter(is_current=True)
            .order_by("-session__name", "name")
            .first()
        )

        if current_term:
            current_session = current_term.session
            previous_term = None

            if current_term.name == Term.TermName.SECOND:
                previous_term = terms.filter(
                    session=current_session,
                    name=Term.TermName.FIRST,
                ).first()

            elif current_term.name == Term.TermName.THIRD:
                previous_term = terms.filter(
                    session=current_session,
                    name=Term.TermName.SECOND,
                ).first()

            elif current_term.name == Term.TermName.FIRST:
                previous_term = (
                    terms.filter(
                        session__name__lt=current_session.name,
                        name=Term.TermName.THIRD,
                    )
                    .order_by("-session__name")
                    .first()
                )

            self.initial["to_session"] = current_session
            self.initial["to_term"] = current_term

            if previous_term:
                self.initial["from_session"] = previous_term.session
                self.initial["from_term"] = previous_term

        from_session = self.initial.get("from_session")
        to_session = self.initial.get("to_session")

        self.fields["from_term"].queryset = terms.filter(
            session=from_session,
        ) if from_session else Term.objects.none()

        self.fields["to_term"].queryset = terms.filter(
            session=to_session,
        ) if to_session else Term.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        from_session = cleaned_data.get("from_session")
        from_term = cleaned_data.get("from_term")
        to_session = cleaned_data.get("to_session")
        to_term = cleaned_data.get("to_term")

        if not all([
            from_session,
            from_term,
            to_session,
            to_term,
        ]):
            return cleaned_data

        if from_term.session_id != from_session.pk:
            self.add_error(
                "from_term",
                "The selected source term does not belong to the selected source session.",
            )

        if to_term.session_id != to_session.pk:
            self.add_error(
                "to_term",
                "The selected destination term does not belong to the selected destination session.",
            )

        if from_term.pk == to_term.pk:
            raise forms.ValidationError(
                "The source term and destination term must be different."
            )

        if self.user and self.user.school:
            school_id = self.user.school.id

            if from_session.school_id != school_id:
                self.add_error(
                    "from_session",
                    "The selected source session does not belong to your school.",
                )

            if to_session.school_id != school_id:
                self.add_error(
                    "to_session",
                    "The selected destination session does not belong to your school.",
                )

            if from_term.session.school_id != school_id:
                self.add_error(
                    "from_term",
                    "The selected source term does not belong to your school.",
                )

            if to_term.session.school_id != school_id:
                self.add_error(
                    "to_term",
                    "The selected destination term does not belong to your school.",
                )

        return cleaned_data