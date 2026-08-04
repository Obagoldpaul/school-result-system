from django import forms
from django.contrib.auth import get_user_model
from .models import Student

User = get_user_model()


class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)

    first_name = forms.CharField(
        max_length=150,
        label="First Name"
    )

    other_name = forms.CharField(
        max_length=150,
        required=False,
        label="Other Name"
    )

    last_name = forms.CharField(
        max_length=150,
        label="Surname"
    )

    email = forms.EmailField(required=False)

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"}
        )
    )

    class Meta:
        model = Student

        fields = [
            "school_class",
            "department",

            "admission_number",
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
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "admission_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        return username

    def clean_admission_number(self):
        admission_number = self.cleaned_data["admission_number"]

        if Student.objects.filter(
            admission_number=admission_number
        ).exists():
            raise forms.ValidationError(
                "This admission number is already in use."
            )

        return admission_number

    def clean_lin(self):
        lin = self.cleaned_data.get("lin")

        if (
            lin
            and Student.objects.filter(
                lin=lin
            ).exists()
        ):
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
        )

        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

        student = super().save(commit=False)
        student.user = user

        if commit:
            student.save()
            self.save_m2m()

        return student