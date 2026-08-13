from django import forms

from .models import SchoolSettings


class SchoolSettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolSettings
        fields = [
            "school_name",
            "school_logo",
            "school_address",
            "school_phone",
            "school_email",
            "principal_name",
            "principal_signature",
            "primary_color",
            "secondary_color",
            "report_card_heading",
            "school_motto",
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
        }