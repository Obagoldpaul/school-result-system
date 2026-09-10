from django import forms

from allocations.models import SubjectAllocation
from academics.models import AcademicSession, Term
from teachers.models import Teacher

from .models import (
    Timetable,
    TimetablePeriod,
    TimetableRequirement,
    TeacherAvailability,
)


class TimetableForm(forms.ModelForm):
    session = forms.ModelChoiceField(
        queryset=AcademicSession.objects.none(),
        empty_label="Select Academic Session",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_session",
            }
        ),
    )

    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        empty_label="Select Academic Term",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_term",
                "disabled": True,
            }
        ),
    )

    class Meta:
        model = Timetable
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. First Term Timetable",
                }
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

        if school is None:
            return

        self.fields["session"].queryset = (
            AcademicSession.objects.filter(
                school=school,
            )
            .order_by("-name")
        )

        self.fields["term"].queryset = Term.objects.filter(
            session__school=school,
        ).select_related("session").order_by(
            "-session__name",
            "name",
        )

    def clean_session(self):
        session = self.cleaned_data.get("session")

        if session is None:
            return session

        if self.school is None or session.school_id != self.school.id:
            raise forms.ValidationError(
                "You can only select an academic session from your school."
            )

        return session

    def clean_term(self):
        term = self.cleaned_data.get("term")

        if term is None:
            return term

        if self.school is None or term.session.school_id != self.school.id:
            raise forms.ValidationError(
                "You can only select a term from your school."
            )

        session = self.cleaned_data.get("session")

        if session is None:
            raise forms.ValidationError(
                "Please select an academic session first."
            )

        if term.session_id != session.id:
            raise forms.ValidationError(
                "The selected term does not belong to the selected academic session."
            )

        return term


class TimetablePeriodForm(forms.ModelForm):
    class Meta:
        model = TimetablePeriod
        fields = [
            "name",
            "period_number",
            "start_time",
            "end_time",
            "is_break",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Period 1",
                }
            ),
            "period_number": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "start_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                },
            ),
            "end_time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                },
            ),
            "is_break": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class TimetableRequirementForm(forms.ModelForm):
    class Meta:
        model = TimetableRequirement
        fields = [
            "allocation",
            "lessons_per_week",
            "double_periods",
        ]
        widgets = {
            "allocation": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "lessons_per_week": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "double_periods": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
        }

    def __init__(self, *args, timetable=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.timetable = timetable

        if timetable is None:
            self.fields["allocation"].queryset = SubjectAllocation.objects.none()
            return

        self.fields["allocation"].queryset = (
            SubjectAllocation.objects.filter(
                school_class__school=timetable.school,
                term=timetable.term,
            )
            .select_related(
                "teacher",
                "subject",
                "school_class",
                "term",
            )
            .order_by(
                "school_class__name",
                "subject__name",
            )
        )

    def clean_allocation(self):
        allocation = self.cleaned_data.get("allocation")

        if allocation is None:
            return allocation

        if self.timetable is None:
            raise forms.ValidationError(
                "A timetable is required before selecting an allocation."
            )

        if allocation.school_class.school_id != self.timetable.school_id:
            raise forms.ValidationError(
                "You can only select an allocation from your school."
            )

        if allocation.term_id != self.timetable.term_id:
            raise forms.ValidationError(
                "You can only select an allocation from the timetable's term."
            )

        return allocation

    def clean(self):
        cleaned_data = super().clean()

        lessons_per_week = cleaned_data.get("lessons_per_week")
        double_periods = cleaned_data.get("double_periods")

        if lessons_per_week is not None and double_periods is not None:
            if double_periods > lessons_per_week // 2:
                self.add_error(
                    "double_periods",
                    "The number of double periods cannot exceed half "
                    "of the weekly lessons.",
                )

        return cleaned_data
    
    
class TeacherAvailabilityForm(forms.ModelForm):
    class Meta:
        model = TeacherAvailability
        fields = ["teacher", "day", "start_time", "end_time"]
        widgets = {
            "teacher": forms.Select(attrs={"class": "form-select"}),
            "day": forms.Select(attrs={"class": "form-select"}),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school

        self.fields["teacher"].queryset = (
            Teacher.objects.filter(user__school=school)
            .select_related("user")
            .order_by("user__last_name", "user__first_name", "user__username")
        )

    def clean_teacher(self):
        teacher = self.cleaned_data.get("teacher")

        if teacher is None:
            return teacher

        if self.school is None or teacher.user.school_id != self.school.id:
            raise forms.ValidationError(
                "You can only select a teacher from your school."
            )

        return teacher