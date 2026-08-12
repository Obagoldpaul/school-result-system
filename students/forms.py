from django import forms
from django.contrib.auth import get_user_model

from .models import Student, SchoolClass, Department

User = get_user_model()


class StudentRegistrationForm(forms.ModelForm):

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

            "admission_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Admission number"
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

            "state_of_origin": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "local_government": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "nationality": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "religion": forms.TextInput(
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
        if user and user.school:
            self.fields["school_class"].queryset = SchoolClass.objects.filter(
                school=user.school
            )

            self.fields["department"].queryset = Department.objects.filter(
                school=user.school
            )

        else:
            self.fields["school_class"].queryset = SchoolClass.objects.none()
            self.fields["department"].queryset = Department.objects.none()


    def clean_admission_number(self):

        admission_number = self.cleaned_data["admission_number"]

        if Student.objects.filter(
            admission_number=admission_number
        ).exists():
            raise forms.ValidationError(
                "This admission number already exists."
            )

        return admission_number


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

        user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            user.save()


        student = super().save(commit=False)

        student.user = user
        
    


        if commit:
            student.save()
            self.save_m2m()


        return student
    
    