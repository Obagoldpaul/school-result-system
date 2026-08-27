from django import forms

from .models import Score, ReportCardExtra
from accounts.permissions import can_edit_principal_remark
from accounts.permissions import user_has_permission


class ScoreEntryForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['ca_score', 'exam_score']


class ReportCardExtraForm(forms.ModelForm):

    class Meta:
        model = ReportCardExtra
        fields = [
            "teacher_remark",
            "principal_remark",
            "responsibility",
            "leadership",
            "hardworking",
            "neatness",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not user_has_permission(
            user,
            "reports.teacher_remark",
        ):
            self.fields.pop(
                "teacher_remark",
                None,
            )

        if not user_has_permission(
            user,
            "reports.principal_remark",
        ):
            self.fields.pop(
                "principal_remark",
                None,
            )