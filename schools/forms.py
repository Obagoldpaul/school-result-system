from django import forms
from django.contrib.auth import get_user_model
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from .models import (
    School,
    SchoolRole,
    Permission,
    SubscriptionPackage,
    SchoolSubscription,
    PlatformSettings,
)

User = get_user_model()

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
    
    school_type = forms.ChoiceField(
        choices=School.SchoolType.choices,
        label="School Type",
        widget=forms.Select(
            attrs={
                "class": "form-select",
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


class EditSchoolForm(forms.ModelForm):
    """
    Form used by Platform Administrators to edit the basic
    information of an existing school.

    This form does not change:
        - Subscription
        - School administrator accounts
        - Users
        - Academic structure

    Changing school_type here only updates the school's
    recorded school type. It does not automatically create
    or remove classes or subjects.
    """

    class Meta:
        model = School
        fields = [
            "name",
            "code",
            "school_type",
            "email",
            "phone",
            "address",
            "logo",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Great Goshenland Blossom School",
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. GGBS",
                }
            ),

            "school_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "school@example.com",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 08012345678",
                }
            ),

            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "School address",
                }
            ),

            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "name": "School Name",
            "code": "School Code",
            "school_type": "School Type",
            "email": "Email",
            "phone": "Phone",
            "address": "Address",
            "logo": "School Logo",
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()

        existing_school = School.objects.filter(
            code__iexact=code
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if existing_school:
            raise forms.ValidationError(
                "A school with this code already exists."
            )

        return code

class SchoolSubscriptionForm(forms.ModelForm):
    """
    Form used by Platform Administrators to change
    an existing school's subscription package,
    billing cycle, and start date.

    End date is calculated automatically from the
    selected start date and billing cycle.
    """

    class Meta:
        model = SchoolSubscription
        fields = [
            "package",
            "billing_cycle",
            "start_date",
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

            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

        labels = {
            "package": "Subscription Package",
            "billing_cycle": "Billing Cycle",
            "start_date": "Start Date",
        }


class PlatformSettingsForm(forms.ModelForm):
    """
    Form used by Platform Administrators to manage
    Paul SchoolHub platform branding.
    """

    class Meta:
        model = PlatformSettings
        fields = [
            "platform_name",
            "platform_logo",
            "platform_primary_color",
            "platform_secondary_color",
            "platform_footer",
        ]

        widgets = {
            "platform_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "platform_logo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "platform_primary_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                }
            ),

            "platform_secondary_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                }
            ),

            "platform_footer": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "platform_name": "Platform Name",
            "platform_logo": "Platform Logo",
            "platform_primary_color": "Primary Colour",
            "platform_secondary_color": "Secondary Colour",
            "platform_footer": "Platform Footer",
        }
        
        
class SchoolRoleForm(forms.ModelForm):
    """
    Form for creating and editing a school's custom role.
    """

    class Meta:
        model = SchoolRole
        fields = [
            "name",
            "base_role",
            "description",
            "permissions",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Examination Officer",
                }
            ),

            "base_role": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Describe the responsibilities of this role."
                    ),
                }
            ),

            "permissions": forms.CheckboxSelectMultiple(),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

        self.fields["permissions"].queryset = (
            Permission.objects
            .filter(is_active=True)
            .order_by("module", "name")
        )

        self.fields["permissions"].label = "Permissions"

        # PLATFORM_ADMIN must never be selectable
        # when creating a school-level role.
        self.fields["base_role"].choices = [
            choice
            for choice in self.fields["base_role"].choices
            if choice[0] != "PLATFORM_ADMIN"
        ]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise forms.ValidationError(
                "Role name is required."
            )

        return name


class AssignSchoolRoleForm(forms.ModelForm):
    """
    Assign a configurable SchoolRole to a user.

    The available roles are restricted to the user's school
    by the view.
    """

    class Meta:
        model = User
        fields = ["school_role"]
        widgets = {
            "school_role": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["school_role"].queryset = SchoolRole.objects.none()

        if school is not None:
            self.fields["school_role"].queryset = SchoolRole.objects.filter(
                school=school,
                is_active=True,
            ).order_by("name")

            self.fields["school_role"].label = "School Role"
            self.fields["school_role"].required = False
            

class CreateSchoolUserForm(forms.ModelForm):
    """
    Form for Platform Administrators to create a basic
    administrative user account for a specific school.

    This form is intentionally separate from the existing
    TeacherRegistrationForm and StudentRegistrationForm.

    It is for creating ADMIN accounts from:
        Platform → School → Users

    Teachers and Students should continue to be registered
    through their existing modules.
    """

    password = forms.CharField(
        min_length=8,
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Minimum 8 characters",
            }
        ),
    )

    password_confirm = forms.CharField(
        min_length=8,
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Re-enter password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "other_name",
            "last_name",
            "email",
            "phone_number",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Username",
                }
            ),

            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First name",
                }
            ),

            "other_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Other name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Surname",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(
            username__iexact=username
        ).exists():
            raise forms.ValidationError(
                "This username is already in use."
            )

        return username

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error(
                    "password_confirm",
                    "The passwords do not match."
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # This form creates an ADMIN account only.
        user.role = User.Role.ADMIN

        # The view will provide the school.
        if self.school is not None:
            user.school = self.school

        user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            user.save()

        return user

class EditSchoolUserForm(forms.ModelForm):
    """
    Form for Platform Administrators to edit an existing
    administrative user account belonging to a specific school.

    This form does not change:
        - Account Type
        - School
        - School Role
        - Password

    Those responsibilities are handled separately.
    """

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "other_name",
            "last_name",
            "email",
            "phone_number",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Username",
                }
            ),

            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "First name",
                }
            ),

            "other_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Other name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Surname",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Email address",
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "username": "Username",
            "first_name": "First Name",
            "other_name": "Other Name",
            "last_name": "Surname",
            "email": "Email",
            "phone_number": "Phone Number",
            "is_active": "Active Account",
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        existing_user = User.objects.filter(
            username__iexact=username
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if existing_user:
            raise forms.ValidationError(
                "This username is already in use."
            )

        return username