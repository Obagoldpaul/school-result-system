from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from accounts.normalization import (
    normalize_email,
    normalize_person_name,
)
from core.choices import (
    NIGERIAN_LGAS,
    NIGERIAN_STATES,
    NATIONALITY_CHOICES,
    RELIGION_CHOICES,
)
from core.utils.image_optimizer import optimize_image

from students.models import SchoolClass, Department, Student

from .models import RegistrationApplication


User = get_user_model()


class RegistrationApplicantFieldsMixin:
    """
    Shared applicant identity and personal-information fields.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autocomplete": "username",
            }
        ),
    )

    first_name = forms.CharField(
        max_length=150,
        label="First Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First name",
            }
        ),
    )

    other_name = forms.CharField(
        max_length=150,
        required=False,
        label="Other Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Other name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        label="Surname",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Surname",
            }
        ),
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email address",
                "autocomplete": "email",
            }
        ),
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Phone number",
            }
        ),
    )

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    gender = forms.ChoiceField(
        choices=RegistrationApplication._meta.get_field(
            "gender"
        ).choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    nationality = forms.ChoiceField(
        choices=NATIONALITY_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    state_of_origin = forms.ChoiceField(
        choices=NIGERIAN_STATES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    local_government = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    religion = forms.ChoiceField(
        choices=RELIGION_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    home_address = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Home address",
            }
        ),
    )

    passport = forms.ImageField(
        required=True,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
            }
        ),
    )

    def _setup_lga_choices(self):
        selected_state = self.data.get("state_of_origin")

        if selected_state:
            lgas = NIGERIAN_LGAS.get(
                selected_state,
                [],
            )

            self.fields["local_government"].choices = [
                (lga, lga)
                for lga in lgas
            ]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(
            username__iexact=username
        ).exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        if RegistrationApplication.objects.filter(
            username__iexact=username,
            status=RegistrationApplication.Status.PENDING,
        ).exists():
            raise forms.ValidationError(
                "This username is already being used by a pending registration."
            )

        return username

    def clean_passport(self):
        passport = self.cleaned_data.get("passport")

        if passport:
            return optimize_image(passport)

        return passport


class StudentRegistrationApplicationForm(
    RegistrationApplicantFieldsMixin,
    forms.ModelForm,
):
    """
    Public student registration application.

    This form creates a RegistrationApplication only.
    It does not create a User or Student.
    """

    nationality = forms.ChoiceField(
        choices=NATIONALITY_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    
    state_of_origin = forms.ChoiceField(
        choices=NIGERIAN_STATES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    
    religion = forms.ChoiceField(
        choices=RELIGION_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    
    local_government = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "type": "date",
                "class": "form-control",
            },
        ),
        input_formats=["%Y-%m-%d"],
    )
    
    requested_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(),
        label="Class",
        empty_label="Select class",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    requested_department = forms.ModelChoiceField(
        queryset=Department.objects.none(),
        label="Department",
        required=False,
        empty_label="Select department",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    guardian_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Guardian name",
            }
        ),
    )

    guardian_relationship = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Relationship to student",
            }
        ),
    )

    guardian_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Guardian phone",
            }
        ),
    )

    guardian_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Guardian email",
            }
        ),
    )

    blood_group = forms.ChoiceField(
        choices=[
            ("", "Select blood group"),
            *Student.BLOOD_GROUPS,
        ],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    genotype = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Genotype",
            }
        ),
    )

    medical_condition = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Medical condition, if any",
            }
        ),
    )

    previous_school = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Previous school",
            }
        ),
    )

    class Meta:
        model = RegistrationApplication
        fields = [
            "username",
            "first_name",
            "other_name",
            "last_name",
            "email",
            "phone_number",
            "date_of_birth",
            "gender",
            "nationality",
            "state_of_origin",
            "local_government",
            "religion",
            "home_address",
            "passport",
            "requested_class",
            "requested_department",
            "guardian_name",
            "guardian_relationship",
            "guardian_phone",
            "guardian_email",
            "blood_group",
            "genotype",
            "medical_condition",
            "previous_school",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school
        self.instance.school = school

        self._setup_lga_choices()

        if school:
            self.fields["requested_class"].queryset = (
                SchoolClass.objects.filter(
                    school=school,
                    is_active=True,
                ).order_by(
                    "section",
                    "name",
                )
            )

            self.fields["requested_department"].queryset = (
                Department.objects.filter(
                    school=school,
                ).order_by("name")
            )

    def save(self, commit=True):
        application = super().save(commit=False)

        application.school = self.school
        application.role = RegistrationApplication.Role.STUDENT
        application.status = RegistrationApplication.Status.PENDING

        application.first_name = normalize_person_name(
            self.cleaned_data["first_name"]
        )
        application.other_name = normalize_person_name(
            self.cleaned_data.get("other_name", "")
        )
        application.last_name = normalize_person_name(
            self.cleaned_data["last_name"]
        )
        application.email = normalize_email(
            self.cleaned_data["email"]
        )

        if commit:
            application.save()

        return application


class TeacherRegistrationApplicationForm(
    RegistrationApplicantFieldsMixin,
    forms.ModelForm,
):
    """
    Public teacher registration application.

    This form creates a RegistrationApplication only.
    It does not create a User or Teacher.
    """

    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "type": "date",
                "class": "form-control",
            },
        ),
        input_formats=["%Y-%m-%d"],
    )

    gender = forms.ChoiceField(
        choices=RegistrationApplication._meta.get_field(
            "gender"
        ).choices,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    nationality = forms.ChoiceField(
        choices=NATIONALITY_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    state_of_origin = forms.ChoiceField(
        choices=NIGERIAN_STATES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    local_government = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    religion = forms.ChoiceField(
        choices=RELIGION_CHOICES,
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    qualification = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Qualification",
            }
        ),
    )

    certificate = forms.FileField(
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "application/pdf,image/*",
            }
        ),
    )

    years_of_experience = forms.IntegerField(
        min_value=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "placeholder": "Years of experience",
            }
        ),
    )
    
    bank_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Bank name",
            }
        ),
    )

    account_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Account name",
            }
        ),
    )

    account_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Account number",
                "inputmode": "numeric",
            }
        ),
    )

    class Meta:
        model = RegistrationApplication
        fields = [
            "username",
            "first_name",
            "other_name",
            "last_name",
            "email",
            "phone_number",
            "date_of_birth",
            "gender",
            "nationality",
            "state_of_origin",
            "local_government",
            "religion",
            "home_address",
            "passport",
            "qualification",
            "certificate",
            "years_of_experience",
            "bank_name",
            "account_name",
            "account_number",
        ]

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school
        self.instance.school = school

        self._setup_lga_choices()

    def save(self, commit=True):
        application = super().save(commit=False)

        application.school = self.school
        application.role = RegistrationApplication.Role.TEACHER
        application.status = RegistrationApplication.Status.PENDING

        application.first_name = normalize_person_name(
            self.cleaned_data["first_name"]
        )
        application.other_name = normalize_person_name(
            self.cleaned_data.get("other_name", "")
        )
        application.last_name = normalize_person_name(
            self.cleaned_data["last_name"]
        )
        application.email = normalize_email(
            self.cleaned_data["email"]
        )

        if commit:
            application.save()

        return application