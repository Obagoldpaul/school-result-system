
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User
from schools.models import SchoolRole


class UserAdminForm(forms.ModelForm):

    class Meta:
        model = User
        fields = "__all__"
        
    class Media:
        js = (
            "accounts/js/user_admin.js",
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Start with no school roles.
        self.fields["school_role"].queryset = (
            SchoolRole.objects.none()
        )

        school = None

        # ---------------------------------------------------------
        # EDITING EXISTING USER
        # ---------------------------------------------------------

        if self.instance and self.instance.pk:
            school = self.instance.school

        # ---------------------------------------------------------
        # CREATING / SUBMITTING USER
        # ---------------------------------------------------------

        elif self.data.get("school"):

            try:
                school_id = int(self.data.get("school"))

                from schools.models import School

                school = School.objects.filter(
                    id=school_id
                ).first()

            except (ValueError, TypeError):
                school = None

        # ---------------------------------------------------------
        # FILTER SCHOOL ROLES
        # ---------------------------------------------------------

        if school:

            self.fields["school_role"].queryset = (
                SchoolRole.objects.filter(
                    school=school,
                    is_active=True,
                ).order_by("name")
            )

    def clean(self):

        cleaned_data = super().clean()

        school = cleaned_data.get("school")
        school_role = cleaned_data.get("school_role")

        # ---------------------------------------------------------
        # ROLE REQUIRES SCHOOL
        # ---------------------------------------------------------

        if school_role and not school:

            raise forms.ValidationError(
                "A school must be selected before assigning a school role."
            )

        # ---------------------------------------------------------
        # PREVENT CROSS-SCHOOL ROLE ASSIGNMENT
        # ---------------------------------------------------------

        if (
            school
            and school_role
            and school_role.school_id != school.id
        ):

            raise forms.ValidationError(
                "The selected school role does not belong "
                "to the selected school."
            )

        return cleaned_data

class UserAdminAddForm(UserCreationForm):

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "school",
            "school_role",
            "role",
            "phone_number",
            "other_name",
        )

    class Media:
        js = (
            "accounts/js/user_admin.js",
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["school_role"].queryset = (
            SchoolRole.objects.none()
        )

        school = None

        if self.data.get("school"):

            try:
                school_id = int(
                    self.data.get("school")
                )

                from schools.models import School

                school = School.objects.filter(
                    id=school_id
                ).first()

            except (ValueError, TypeError):
                school = None

        if school:

            self.fields["school_role"].queryset = (
                SchoolRole.objects.filter(
                    school=school,
                    is_active=True,
                ).order_by("name")
            )

    def clean(self):

        cleaned_data = super().clean()

        school = cleaned_data.get("school")
        school_role = cleaned_data.get("school_role")

        if school_role and not school:

            raise forms.ValidationError(
                "A school must be selected before assigning "
                "a school role."
            )

        if (
            school
            and school_role
            and school_role.school_id != school.id
        ):

            raise forms.ValidationError(
                "The selected school role does not belong "
                "to the selected school."
            )

        return cleaned_data
