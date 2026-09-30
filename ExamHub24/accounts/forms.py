from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import StudentProfile, User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    referral_code = forms.CharField(max_length=20, required=False, help_text="Have a friend's referral code? Enter it for a signup bonus.")
    institution_code = forms.CharField(max_length=20, required=False, help_text="Studying at a coaching institute partnered with us? Enter their code.")

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone_number', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError('An account with this phone number already exists.')
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.is_active = True  # kept active; is_verified toggled after OTP confirmation
        if commit:
            user.save()
        return user


class OTPForm(forms.Form):
    otp_code = forms.CharField(max_length=6, label='Enter OTP')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'phone_number', 'date_of_birth', 'gender', 'profile_picture', 'state', 'city']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['target_exam', 'education_level', 'college_name']
