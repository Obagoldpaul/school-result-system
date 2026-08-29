from django import forms
from django.contrib.auth import get_user_model

from .models import Teacher
from students.models import SchoolClass

from core.choices import (
    NIGERIAN_STATES,
    NATIONALITY_CHOICES,
    RELIGION_CHOICES,
    NIGERIAN_LGAS,
)

User = get_user_model()


class TeacherRegistrationForm(forms.ModelForm):

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

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password"
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

    employment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control"
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


    class Meta:

        model = Teacher

        fields = [

            # Personal
            "passport",
            "phone_number",
            "date_of_birth",
            "gender",
            "home_address",
            "state_of_origin",
            "local_government",
            "nationality",
            "religion",

            # Professional
            "staff_id",
            "qualification",
            "certificate",
            "years_of_experience",
            "employment_date",
            
            # Payment
            "bank_name",
            "account_name",
            "account_number",

            # Responsibility
            "is_class_teacher",
            "assigned_class",
        ]


        widgets = {

            "home_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Teacher home address"
                }
            ),

            "gender": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "assigned_class": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "is_class_teacher": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number"
                }
            ),

            "staff_id": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Staff ID"
                }
            ),

            "qualification": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "certificate": forms.FileInput(
                attrs={
                    "class": "form-control",
                     "accept": "application/pdf,image/*"
                }
            ),

            "years_of_experience": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            ),
            
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bank name"
                }
            ),

            "account_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account name"
                }
            ),

            "account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account number"
                }
            ),

            "passport": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*"
                }
            ),
        }
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.user = user

        selected_state = None

        if self.data:
            selected_state = self.data.get("state_of_origin")

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
            self.fields["assigned_class"].queryset = SchoolClass.objects.filter(
                school=user.school
            )
        else:
            self.fields["assigned_class"].queryset = SchoolClass.objects.none()


    def clean_username(self):

        username = self.cleaned_data["username"]

        if User.objects.filter(
            username=username
        ).exists():

            raise forms.ValidationError(
                "This username is already taken."
            )

        return username



    def clean_staff_id(self):

        staff_id = self.cleaned_data["staff_id"]

        if not self.user or not self.user.school:
            return staff_id

        if Teacher.objects.filter(
            staff_id=staff_id,
            user__school=self.user.school,
        ).exists():

            raise forms.ValidationError(
                "This staff ID already exists in this school."
            )

        return staff_id



    def save(self, commit=True, user=None):

        new_user = User(
            username=self.cleaned_data["username"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            other_name=self.cleaned_data.get(
                "other_name",
                ""
            ),
            email=self.cleaned_data.get(
                "email",
                ""
            ),
            role=User.Role.TEACHER,
        )

        if user and user.school:
            new_user.school = user.school

        new_user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            new_user.save()

        teacher = super().save(
            commit=False
        )

        teacher.user = new_user

        if commit:
            teacher.save()

        return teacher
