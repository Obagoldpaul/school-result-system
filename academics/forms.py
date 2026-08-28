from django import forms

from .models import SchoolSettings
from schools.models import School


class SchoolSettingsForm(forms.ModelForm):

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.school = school

        subscription = None

        if school:
            try:
                subscription = school.subscription
            except school.subscription.RelatedObjectDoesNotExist:
                subscription = None

        package_name = (
            subscription.package.name
            if subscription and subscription.is_active
            else None
        )

        # -------------------------------------------------
        # USE THE MAIN SCHOOL RECORD AS SOURCE OF TRUTH
        # -------------------------------------------------

        if school:
            self.initial["school_name"] = school.name
            self.initial["school_address"] = school.address
            self.initial["school_phone"] = school.phone
            self.initial["school_email"] = school.email

            if school.logo:
                self.initial["school_logo"] = school.logo

        # -------------------------------------------------
        # PACKAGE-BASED BRANDING ACCESS
        # -------------------------------------------------

        if package_name == "BASIC":
            for field_name in [
                "school_logo",
                "principal_signature",
                "primary_color",
                "secondary_color",
                "report_card_heading",
                "school_motto",
            ]:
                self.fields.pop(field_name, None)

        elif package_name == "STANDARD":
            for field_name in [
                "school_logo",
                "principal_signature",
                "primary_color",
                "secondary_color",
                "school_motto",
            ]:
                self.fields.pop(field_name, None)

        # Premium keeps all branding fields.

    class Meta:
        model = SchoolSettings
        fields = [
            "school_name",
            "school_logo",
            "school_address",
            "school_phone",
            "school_email",
            "bank_name",
            "account_name",
            "account_number",
            "principal_name",
            "principal_signature",
            "primary_color",
            "secondary_color",
            "report_card_heading",
            "school_motto",
            "show_class_position",
        ]

        widgets = {
            "school_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "school_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "school_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "school_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                }
            ),
            
            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. First Bank",
                }
            ),

            "account_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Great Goshenland Blossom School",
                }
            ),

            "account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 0123456789",
                    "inputmode": "numeric",
                }
            ),
            
            "principal_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "primary_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                }
            ),
            "secondary_color": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "type": "color",
                }
            ),
            "report_card_heading": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "school_motto": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "show_class_position": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }