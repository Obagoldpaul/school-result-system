from django import forms
from .models import Score


class ScoreEntryForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['ca_score', 'exam_score']


from .models import ReportCardExtra


class ReportCardExtraForm(forms.ModelForm):
    class Meta:
        model = ReportCardExtra
        fields = ['days_present', 'days_school_opened', 'teacher_remark', 'principal_remark']

    def clean(self):
        cleaned_data = super().clean()
        days_present = cleaned_data.get('days_present')
        days_school_opened = cleaned_data.get('days_school_opened')

        if days_present is not None and days_school_opened is not None:
            if days_present > days_school_opened:
                raise forms.ValidationError(
                    "Days present cannot be greater than days school opened."
                )
        return cleaned_data