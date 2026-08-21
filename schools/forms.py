from django import forms

from accounts.models import User
from .models import School, SubscriptionPackage, SchoolSubscription


class SchoolRegistrationForm(forms.Form):
    """
    Form used by Platform Administrators to register a new school
    together with its first school administrator.
    """

    # ---------------------------------------------------------
    # SCHOOL INFORMATION
    # ---------------------------------------------------------

    school_name = forms.CharField(
        max_length=200,
        label="School Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Great Goshenland Blossom School",
            }
        ),
    )

    school_code = forms.CharField(
        max_length=20,
        label="School Code",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. GGBS",
            }
        ),
    )

    email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "school@example.com",
            }
        ),
    )

    phone = forms.CharField(
        max_length=30,
        required=False,
        label="Phone",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 08012345678",
            }
        ),
    )

    address = forms.CharField(
        required=False,
        label="Address",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "School address",
            }
        ),
    )

    # ---------------------------------------------------------
    # SUBSCRIPTION
    # ---------------------------------------------------------

    package = forms.ModelChoiceField(
        queryset=SubscriptionPackage.objects.filter(
            is_active=True
        ),
        label="Package",
        empty_label="Select Package",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    billing_cycle = forms.ChoiceField(
        choices=SchoolSubscription.BillingCycle.choices,
        label="Subscription",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # ---------------------------------------------------------
    # ADMINISTRATOR
    # ---------------------------------------------------------

    admin_first_name = forms.CharField(
        max_length=150,
        label="First Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Administrator first name",
            }
        ),
    )

    admin_last_name = forms.CharField(
        max_length=150,
        label="Last Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Administrator last name",
            }
        ),
    )

    admin_username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Administrator username",
            }
        ),
    )

    admin_email = forms.EmailField(
        label="Administrator Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "admin@example.com",
            }
        ),
    )

    admin_password = forms.CharField(
        min_length=8,
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Minimum 8 characters",
            }
        ),
    )

    admin_password_confirm = forms.CharField(
        min_length=8,
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter administrator password",
            }
        ),
    )

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def clean_school_code(self):
        code = self.cleaned_data["school_code"].strip().upper()

        if School.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError(
                "A school with this code already exists."
            )

        return code

    def clean_admin_username(self):
        username = self.cleaned_data["admin_username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already in use."
            )

        return username

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("admin_password")
        password_confirm = cleaned_data.get("admin_password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error(
                    "admin_password_confirm",
                    "The passwords do not match."
                )

        return cleaned_data
    

class SchoolSubscriptionForm(forms.ModelForm):
    """
    Form used by Platform Administrators to change
    an existing school's subscription package and billing cycle.
    """

    class Meta:
        model = SchoolSubscription
        fields = [
            "package",
            "billing_cycle",
        ]

        widgets = {
            "package": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "billing_cycle": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

        }

        labels = {
            "package": "Subscription Package",
            "billing_cycle": "Billing Cycle",
        }
