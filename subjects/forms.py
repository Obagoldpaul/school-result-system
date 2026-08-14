from django import forms

from .models import Subject, ClassSubject
from students.models import SchoolClass


class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject
        fields = [
            'name',
            'code',
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

        if user and user.is_authenticated and user.school:
            self.fields["parent"].queryset = (
                Subject.objects.filter(
                    school=user.school,
                    is_active=True,
                )
                .exclude(pk=self.instance.pk)
            )
        else:
            self.fields["parent"].queryset = Subject.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        if not self.user or not self.user.school:
            raise forms.ValidationError(
                "A school is required to create a subject."
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

        if user and user.is_authenticated and user.school:

            self.fields["school_class"].queryset = (
                user.school.classes.all()
            )

            self.fields["subject"].queryset = Subject.objects.filter(
                school=user.school,
                is_active=True,
            )

        else:

            self.fields["school_class"].queryset = (
                self.fields["school_class"].queryset.none()
            )

            self.fields["subject"].queryset = (
                self.fields["subject"].queryset.none()
            )

    def clean(self):
        cleaned_data = super().clean()

        school_class = cleaned_data.get("school_class")
        subject = cleaned_data.get("subject")

        if not self.user or not self.user.school:
            raise forms.ValidationError(
                "A school is required for this operation."
            )

        if school_class and school_class.school_id != self.user.school_id:
            self.add_error(
                "school_class",
                "The selected class does not belong to your school."
            )

        if subject and subject.school_id != self.user.school_id:
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

            self.fields["school_class"].queryset = (
                SchoolClass.objects.filter(
                    school=user.school
                ).order_by("name")
            )

            self.fields["subjects"].queryset = (
                Subject.objects.filter(
                    school=user.school,
                    is_active=True,
                ).order_by("name")
            )