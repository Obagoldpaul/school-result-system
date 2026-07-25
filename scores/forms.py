from django import forms
from .models import Score


class ScoreEntryForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['ca_score', 'exam_score']