from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 3,
                'maxlength': 200,
                'placeholder': 'Tell something about yourself...',
            }),
            'avatar': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
            }),
        }