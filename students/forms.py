from django import forms
from django.contrib.auth import get_user_model
import re
from .models import Student, SchoolClass, Department
from core.choices import (
    NIGERIAN_STATES,
    NIGERIAN_LGAS,
    NATIONALITY_CHOICES,
    RELIGION_CHOICES,
)

User = get_user_model()

def generate_admission_number(school):
    prefix = f"{school.code.upper()}-STU-"

    existing_numbers = Student.objects.filter(
        user__school=school
    ).values_list(
        "admission_number",
        flat=True
    )

    highest_number = 0

    pattern = re.compile(
        rf"^{re.escape(prefix)}(\d+)$"
    )

    for admission_number in existing_numbers:
        match = pattern.match(admission_number or "")

        if match:
            number = int(match.group(1))

            if number > highest_number:
                highest_number = number

    next_number = highest_number + 1

    return f"{prefix}{next_number:03d}"

class GroupedSchoolClassChoiceField(forms.ModelChoiceField):

    def __iter__(self):
        if self.empty_label is not None:
            yield ("", self.empty_label)

        queryset = self.queryset.order_by(
            "section",
            "name",
        )

        section_labels = dict(
            SchoolClass.Section.choices
        )

        for section in [
            SchoolClass.Section.PRE_PRIMARY,
            SchoolClass.Section.PRIMARY,
            SchoolClass.Section.JUNIOR_SECONDARY,
            SchoolClass.Section.SENIOR_SECONDARY,
        ]:

            classes = queryset.filter(
                section=section
            )

            if not classes.exists():
                continue

            yield (
                section_labels[section],
                [
                    (
                        self.prepare_value(obj),
                        self.label_from_instance(obj),
                    )
                    for obj in classes
                ],
            )

class StudentRegistrationForm(forms.ModelForm):

    school_class = GroupedSchoolClassChoiceField(
        queryset=SchoolClass.objects.none(),
        empty_label="Select class",
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username"
            }
        )
    )

    first_name = forms.CharField(
        max_length=150,
        label="First Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First name"
            }
        )
    )

    other_name = forms.CharField(
        max_length=150,
        required=False,
        label="Other Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Other name"
            }
        )
    )

    last_name = forms.CharField(
        max_length=150,
        label="Surname",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Surname"
            }
        )
    )

    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address"
            }
        )
    )

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control"
            }
        )
    )
    
    state_of_origin = forms.ChoiceField(
        choices=NIGERIAN_STATES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    local_government = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    nationality = forms.ChoiceField(
        choices=NATIONALITY_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    religion = forms.ChoiceField(
        choices=RELIGION_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select"
            }
        )
    )

    class Meta:

        model = Student

        fields = [
            "school_class",
            "department",

            "lin",

            "passport",

            "date_of_birth",
            "gender",

            "state_of_origin",
            "local_government",
            "nationality",
            "religion",

            "home_address",

            "blood_group",
            "genotype",

            "guardian_name",
            "guardian_relationship",
            "guardian_phone",
            "guardian_email",

            "emergency_contact_name",
            "emergency_contact_phone",

            "medical_condition",

            "admission_date",
            "previous_school",
            "admission_status",
        ]

        widgets = {

            "school_class": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "department": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "gender": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "blood_group": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "admission_status": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "lin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Learner Identification Number"
                }
            ),

            "passport": forms.FileInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "home_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),

            "genotype": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "guardian_name": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "guardian_relationship": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "guardian_phone": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "guardian_email": forms.EmailInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "emergency_contact_name": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "emergency_contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "medical_condition": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),

            "admission_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),

            "previous_school": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),
        }


    def clean_username(self):

        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        return username
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user
        
        selected_state = None

        if self.data:
            selected_state = self.data.get("state_of_origin")
        elif self.instance and self.instance.pk:
            selected_state = self.instance.state_of_origin

        if selected_state:
            lgas = NIGERIAN_LGAS.get(
                selected_state,
                []
            )

            self.fields["local_government"].choices = [
                (lga, lga)
                for lga in lgas
            ]

        if user and user.school:

            classes = SchoolClass.objects.filter(
                school=user.school,
                is_active=True
            )
            
            self.fields["school_class"].queryset = classes

            section_order = [
                SchoolClass.Section.PRE_PRIMARY,
                SchoolClass.Section.PRIMARY,
                SchoolClass.Section.JUNIOR_SECONDARY,
                SchoolClass.Section.SENIOR_SECONDARY,
            ]

            section_labels = dict(
                SchoolClass.Section.choices
            )

            grouped_choices = [
                ("", "Select class")
            ]

            for section in section_order:

                section_classes = classes.filter(
                    section=section
                ).order_by("name")

                if section_classes.exists():

                    grouped_choices.append(
                        (
                            section_labels[section],
                            [
                                (
                                    str(school_class.id),
                                    school_class.name
                                )
                                for school_class in section_classes
                            ]
                        )
                    )

            self.fields["school_class"].choices = grouped_choices

            self.fields["department"].queryset = Department.objects.filter(
                school=user.school
            )

        else:

            self.fields["school_class"].queryset = SchoolClass.objects.none()

            self.fields["department"].queryset = Department.objects.none()


    def clean_lin(self):

        lin = self.cleaned_data.get("lin")

        if lin and Student.objects.filter(
            lin=lin
        ).exists():
            raise forms.ValidationError(
                "This LIN already exists."
            )

        return lin


    def save(self, commit=True):

        user = User(
            username=self.cleaned_data["username"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            other_name=self.cleaned_data.get("other_name", ""),
            email=self.cleaned_data.get("email", ""),
            role=User.Role.STUDENT,
            school=self.user.school,
        )

        user.set_unusable_password()

        if commit:
            user.save()


        student = super().save(commit=False)

        student.user = user

        if self.user and self.user.school:
            student.admission_number = generate_admission_number(
                self.user.school
            )

        if commit:
            student.save()
            self.save_m2m()

        return student

class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ["name", "section"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. BASIC 1",
                }
            ),
            "section": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    