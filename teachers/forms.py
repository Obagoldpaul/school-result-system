from django import forms
from django.contrib.auth import get_user_model
from .models import Teacher

User = get_user_model()


class TeacherRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Teacher
        fields = [
            'staff_id', 'phone_number', 'qualification',
            'is_class_teacher', 'assigned_class',
        ]

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_staff_id(self):
        staff_id = self.cleaned_data['staff_id']
        if Teacher.objects.filter(staff_id=staff_id).exists():
            raise forms.ValidationError("This staff ID is already in use.")
        return staff_id

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data.get('email', ''),
            role=User.Role.TEACHER,
        )
        user.set_password(self.cleaned_data['password'])
        user.save()

        teacher = super().save(commit=False)
        teacher.user = user
        if commit:
            teacher.save()
        return teacher