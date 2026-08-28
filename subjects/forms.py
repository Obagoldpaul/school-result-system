from django import forms

from .models import Subject, ClassSubject
from students.models import SchoolClass


class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject
        fields = [
            'name',
            'code',
            'level',
            'parent',
            'is_elective',
        ]

        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Subject name',
                }
            ),

            'code': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Subject code',
                }
            ),

            'level': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'parent': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'is_elective': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        # --------------------------------------------------
        # NO SCHOOL
        # --------------------------------------------------

        if not (
            user
            and user.is_authenticated
            and user.school
        ):
            self.fields["level"].choices = []
            self.fields["parent"].queryset = (
                Subject.objects.none()
            )
            return

        school = user.school

        # --------------------------------------------------
        # DETERMINE ALLOWED SUBJECT LEVELS
        # --------------------------------------------------

        if school.school_type == school.SchoolType.PRIMARY:

            allowed_levels = [
                Subject.SubjectLevel.PRIMARY
            ]

        elif school.school_type == school.SchoolType.SECONDARY:

            allowed_levels = [
                Subject.SubjectLevel.SECONDARY
            ]

        else:

            # PRIMARY_SECONDARY
            allowed_levels = [
                Subject.SubjectLevel.PRIMARY,
                Subject.SubjectLevel.SECONDARY,
            ]

        # --------------------------------------------------
        # LEVEL FIELD
        # --------------------------------------------------

        self.fields["level"].choices = [
            (
                level,
                Subject.SubjectLevel(level).label
            )
            for level in allowed_levels
        ]

        # --------------------------------------------------
        # DETERMINE SELECTED LEVEL
        # --------------------------------------------------

        selected_level = None

        if self.is_bound:
            selected_level = self.data.get(
                self.add_prefix("level")
            )

        if not selected_level and self.instance.pk:
            selected_level = self.instance.level

        # --------------------------------------------------
        # PARENT SUBJECTS
        # --------------------------------------------------

        parent_queryset = Subject.objects.filter(
            school=school,
            is_active=True,
        ).exclude(
            pk=self.instance.pk
        )

        if selected_level in allowed_levels:
            parent_queryset = parent_queryset.filter(
                level=selected_level
            )
        else:
            parent_queryset = parent_queryset.filter(
                level__in=allowed_levels
            )

        self.fields["parent"].queryset = (
            parent_queryset.order_by("name")
        )

    def clean(self):
        cleaned_data = super().clean()

        if not self.user or not self.user.school:
            raise forms.ValidationError(
                "A school is required to create a subject."
            )

        school = self.user.school
        level = cleaned_data.get("level")

        # --------------------------------------------------
        # SCHOOL TYPE → SUBJECT LEVEL VALIDATION
        # --------------------------------------------------

        if school.school_type == school.SchoolType.PRIMARY:

            allowed_levels = [
                Subject.SubjectLevel.PRIMARY
            ]

        elif school.school_type == school.SchoolType.SECONDARY:

            allowed_levels = [
                Subject.SubjectLevel.SECONDARY
            ]

        else:

            allowed_levels = [
                Subject.SubjectLevel.PRIMARY,
                Subject.SubjectLevel.SECONDARY,
            ]

        if level not in allowed_levels:
            self.add_error(
                "level",
                "This subject level is not available for your school."
            )

        # --------------------------------------------------
        # PARENT LEVEL VALIDATION
        # --------------------------------------------------

        parent = cleaned_data.get("parent")

        if parent and level:
            if parent.level != level:
                self.add_error(
                    "parent",
                    "The parent subject must have the same subject level."
                )

        return cleaned_data

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")

        if parent and parent.school_id != self.user.school_id:
            raise forms.ValidationError(
                "The parent subject must belong to your school."
            )

        return parent

    def save(self, commit=True):
        subject = super().save(commit=False)

        subject.school = self.user.school

        if not subject.pk:
            subject.is_active = True

        if commit:
            subject.save()

        return subject


class ClassSubjectForm(forms.ModelForm):

    class Meta:
        model = ClassSubject
        fields = ['school_class', 'subject']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        # --------------------------------------------------
        # NO SCHOOL
        # --------------------------------------------------

        if not (
            user
            and user.is_authenticated
            and user.school
        ):
            self.fields["school_class"].queryset = (
                SchoolClass.objects.none()
            )

            self.fields["subject"].queryset = (
                Subject.objects.none()
            )

            return

        school = user.school

        # --------------------------------------------------
        # SCHOOL CLASSES
        # --------------------------------------------------

        self.fields["school_class"].queryset = (
            SchoolClass.objects.filter(
                school=school
            ).order_by(
                "section",
                "name"
            )
        )

        # --------------------------------------------------
        # DETERMINE SELECTED CLASS
        # --------------------------------------------------

        selected_class = None

        if self.is_bound:
            selected_class_id = self.data.get(
                self.add_prefix("school_class")
            )

            if selected_class_id:
                try:
                    selected_class = SchoolClass.objects.get(
                        id=selected_class_id,
                        school=school,
                    )
                except SchoolClass.DoesNotExist:
                    selected_class = None

        elif self.instance.pk:
            selected_class = self.instance.school_class

        # --------------------------------------------------
        # SUBJECTS
        # --------------------------------------------------

        subject_queryset = Subject.objects.filter(
            school=school,
            is_active=True,
        )

        # --------------------------------------------------
        # CLASS SECTION → SUBJECT LEVEL
        # --------------------------------------------------

        if selected_class:

            if selected_class.section in [
                SchoolClass.Section.PRE_PRIMARY,
                SchoolClass.Section.PRIMARY,
            ]:

                subject_queryset = subject_queryset.filter(
                    level=Subject.SubjectLevel.PRIMARY
                )

            elif selected_class.section in [
                SchoolClass.Section.JUNIOR_SECONDARY,
                SchoolClass.Section.SENIOR_SECONDARY,
            ]:

                subject_queryset = subject_queryset.filter(
                    level=Subject.SubjectLevel.SECONDARY
                )

        self.fields["subject"].queryset = (
            subject_queryset.order_by("name")
        )

    def clean(self):
        cleaned_data = super().clean()

        school_class = cleaned_data.get("school_class")
        subject = cleaned_data.get("subject")

        if not self.user or not self.user.school:
            raise forms.ValidationError(
                "A school is required for this operation."
            )

        if (
            school_class
            and school_class.school_id != self.user.school_id
        ):
            self.add_error(
                "school_class",
                "The selected class does not belong to your school."
            )

        if (
            subject
            and subject.school_id != self.user.school_id
        ):
            self.add_error(
                "subject",
                "The selected subject does not belong to your school."
            )

        return cleaned_data


class BulkClassSubjectForm(forms.Form):

    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        )
    )

    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        if user and user.is_authenticated and user.school:

            school = user.school

            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(
                    school=school
                ).order_by(
                    "section",
                    "name"
                )
            )

            # --------------------------------------------------
            # ALL ACTIVE SUBJECTS FOR THIS SCHOOL
            # --------------------------------------------------

            self.fields["subjects"].queryset = (
                Subject.objects.filter(
                    school=school,
                    is_active=True,
                ).order_by("level", "name")
            )

        else:

            self.fields["school_class"].queryset = (
                SchoolClass.objects.none()
            )

            self.fields["subjects"].queryset = (
                Subject.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        school_class = cleaned_data.get("school_class")
        subjects = cleaned_data.get("subjects")

        if not self.user or not self.user.school:
            raise forms.ValidationError(
                "A school is required for this operation."
            )

        if not school_class:
            return cleaned_data

        # --------------------------------------------------
        # CLASS → SUBJECT LEVEL
        # --------------------------------------------------

        if school_class.section in [
            SchoolClass.Section.PRE_PRIMARY,
            SchoolClass.Section.PRIMARY,
        ]:
            allowed_level = Subject.SubjectLevel.PRIMARY

        elif school_class.section in [
            SchoolClass.Section.JUNIOR_SECONDARY,
            SchoolClass.Section.SENIOR_SECONDARY,
        ]:
            allowed_level = Subject.SubjectLevel.SECONDARY

        else:
            allowed_level = None

        # --------------------------------------------------
        # CLASS SCHOOL VALIDATION
        # --------------------------------------------------

        if school_class.school_id != self.user.school_id:

            self.add_error(
                "school_class",
                "The selected class does not belong to your school."
            )

            return cleaned_data

        # --------------------------------------------------
        # SUBJECT VALIDATION
        # --------------------------------------------------

        if subjects and allowed_level:

            invalid_subjects = subjects.exclude(
                level=allowed_level
            )

            if invalid_subjects.exists():

                self.add_error(
                    "subjects",
                    (
                        f"{school_class.get_section_display()} classes "
                        f"can only be assigned "
                        f"{Subject.SubjectLevel(allowed_level).label} "
                        f"subjects."
                    )
                )

        return cleaned_data