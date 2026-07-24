from django import forms
from django.contrib.auth import get_user_model
from .models import Student, SchoolClass, Department

User = get_user_model()


class StudentRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Student
        fields = [
            'school_class', 'department', 'admission_number',
            'date_of_birth', 'gender', 'guardian_name', 'guardian_phone',
        ]

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data.get('email', ''),
            role=User.Role.STUDENT,
        )
        user.set_password(self.cleaned_data['password'])
        user.save()

        student = super().save(commit=False)
        student.user = user
        if commit:
            student.save()
        return student