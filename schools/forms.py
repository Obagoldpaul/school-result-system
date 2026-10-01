from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
from datetime import timedelta

from dateutil.relativedelta import relativedelta
import re
from .models import (
    School,
    SchoolRole,
    Permission,
    SubscriptionPackage,
    SchoolSubscription,
    PlatformSettings,
    Feature,
    SubscriptionPricing,
    SubscriptionInvoice,
    SubscriptionInvoiceItem,
    SubscriptionPayment,
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

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def clean_school_code(self):
        code = self.cleaned_data["school_code"].strip().upper()

        if not re.fullmatch(r"[A-Z0-9]+", code):
            raise forms.ValidationError(
                "School code must contain only letters and numbers."
            )

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

        school_type = cleaned_data.get("school_type")
        package = cleaned_data.get("package")
        billing_cycle = cleaned_data.get("billing_cycle")

        if school_type and package and billing_cycle:
            pricing_exists = SubscriptionPricing.objects.filter(
                school_type=school_type,
                package=package,
                billing_cycle=billing_cycle,
            ).exists()

            if not pricing_exists:
                raise forms.ValidationError(
                    "No default subscription pricing is configured for "
                    "the selected school type, package, and billing cycle."
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

        if not re.fullmatch(r"[A-Z0-9]+", code):
            raise forms.ValidationError(
                "School code must contain only letters and numbers."
            )

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
    billing cycle, start date, and agreed price.

    End date is calculated automatically from the
    selected start date and billing cycle.
    """

    class Meta:
        model = SchoolSubscription
        fields = [
            "package",
            "billing_cycle",
            "agreed_price",
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

            "agreed_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
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
            "agreed_price": "Agreed Price",
            "start_date": "Start Date",
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

        if school:
            pricing_records = SubscriptionPricing.objects.filter(
                school_type=school.school_type,
            ).select_related("package")

            self.pricing_defaults = {
                f"{pricing.package_id}_{pricing.billing_cycle}": str(
                    pricing.price
                )
                for pricing in pricing_records
            }

            pricing = SubscriptionPricing.objects.filter(
                school_type=school.school_type,
                package=self.instance.package,
                billing_cycle=self.instance.billing_cycle,
            ).first()

            if (
                pricing
                and not self.is_bound
                and not self.instance.agreed_price
            ):
                self.initial["agreed_price"] = pricing.price
        else:
            self.pricing_defaults = {}


class SubscriptionPackageForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPackage
        fields = ["name", "description", "price", "is_active", "features"]
        widgets = {
            "name": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what this package provides.",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "features": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "name": "Package Name",
            "description": "Description",
            "price": "Price",
            "is_active": "Active Package",
            "features": "Features",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["features"].queryset = Feature.objects.filter(
            is_active=True
        )

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
        return super().clean()

    def save(self, commit=True):
        user = super().save(commit=False)

        # This form creates an ADMIN account only.
        user.role = User.Role.ADMIN

        # The view will provide the school.
        if self.school is not None:
            user.school = self.school

        user.set_unusable_password()

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
    
    
class FeatureForm(forms.ModelForm):
    """
    Form used by Platform Administrators to create and edit
    Paul SchoolHub platform features.
    """

    class Meta:
        model = Feature
        fields = [
            "code",
            "name",
            "description",
            "is_active",
        ]

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. TIMETABLE",
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Feature name",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what this feature provides.",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "code": "Feature Code",
            "name": "Feature Name",
            "description": "Description",
            "is_active": "Active Feature",
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()

        existing_feature = Feature.objects.filter(
            code__iexact=code
        ).exclude(
            pk=self.instance.pk
        ).exists()

        if existing_feature:
            raise forms.ValidationError(
                "A feature with this code already exists."
            )

        return code
    
    
    
class SubscriptionPricingForm(forms.ModelForm):
    """
    Form used by Platform Administrators to create and edit
    default subscription pricing for a school type,
    package, and billing cycle.
    """

    class Meta:
        model = SubscriptionPricing
        fields = [
            "school_type",
            "package",
            "billing_cycle",
            "price",
        ]

        widgets = {
            "school_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

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

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }

        labels = {
            "school_type": "School Type",
            "package": "Subscription Package",
            "billing_cycle": "Billing Cycle",
            "price": "Default Price",
        }
        
    def clean(self):
        cleaned_data = super().clean()

        school_type = cleaned_data.get("school_type")
        package = cleaned_data.get("package")
        billing_cycle = cleaned_data.get("billing_cycle")

        if school_type and package and billing_cycle:
            existing_pricing = SubscriptionPricing.objects.filter(
                school_type=school_type,
                package=package,
                billing_cycle=billing_cycle,
            )

            if self.instance.pk:
                existing_pricing = existing_pricing.exclude(
                    pk=self.instance.pk,
                )

            if existing_pricing.exists():
                raise forms.ValidationError(
                    "Default pricing already exists for this "
                    "school type, package, and billing cycle."
                )

        return cleaned_data
    

class SubscriptionInvoiceForm(forms.ModelForm):
    class Meta:
        model = SubscriptionInvoice
        fields = [
            "invoice_date",
            "due_date",
            "discount",
            "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "discount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
        labels = {
            "invoice_date": "Invoice Date",
            "due_date": "Due Date",
            "discount": "Discount",
            "notes": "Notes",
        }


class SubscriptionInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = SubscriptionInvoiceItem
        fields = [
            "description",
            "quantity",
            "unit_price",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }
        labels = {
            "description": "Description",
            "quantity": "Quantity",
            "unit_price": "Unit Price",
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")

        if quantity is not None and quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least 1."
            )

        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get("unit_price")

        if unit_price is not None and unit_price < 0:
            raise forms.ValidationError(
                "Unit price cannot be negative."
            )

        return unit_price


SubscriptionInvoiceItemFormSet = inlineformset_factory(
    SubscriptionInvoice,
    SubscriptionInvoiceItem,
    form=SubscriptionInvoiceItemForm,
    extra=1,
    can_delete=True,
)


class SubscriptionPaymentForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPayment
        fields = [
            "payment_date",
            "amount",
            "payment_method",
            "payment_reference",
            "notes",
        ]
        widgets = {
            "payment_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "payment_method": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "payment_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }
        labels = {
            "payment_date": "Payment Date",
            "amount": "Amount Paid",
            "payment_method": "Payment Method",
            "payment_reference": "Payment Reference",
            "notes": "Notes",
        }