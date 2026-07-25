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