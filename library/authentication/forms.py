"""Django forms for registration, login and editing users."""
from django import forms
from django.contrib.auth import authenticate

from .models import ROLE_CHOICES, CustomUser

PASSWORD_MIN_LENGTH = 6


class RegisterForm(forms.ModelForm):
    """Sign up as a reader (visitor) or as a librarian."""
    role = forms.TypedChoiceField(
        choices=ROLE_CHOICES, coerce=int, initial=0, widget=forms.RadioSelect, label='I am a…')
    password1 = forms.CharField(
        label='Password', widget=forms.PasswordInput,
        min_length=PASSWORD_MIN_LENGTH, help_text=f'At least {PASSWORD_MIN_LENGTH} characters.')
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('role', 'first_name', 'last_name', 'middle_name', 'email')
        labels = {'middle_name': 'Middle name (optional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = forms.EmailField(max_length=100, label='Email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get('password1'), cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = True
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Log in with email and password."""
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email, password = cleaned.get('email'), cleaned.get('password')
        if email and password:
            self.user = authenticate(self.request, username=email.lower(), password=password)
            if self.user is None:
                raise forms.ValidationError('Wrong email or password.')
        return cleaned


class ProfileForm(forms.ModelForm):
    """A user edits his own name."""

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'middle_name')
        labels = {'middle_name': 'Middle name (optional)'}


class UserEditForm(forms.ModelForm):
    """A librarian edits a user."""
    role = forms.TypedChoiceField(choices=ROLE_CHOICES, coerce=int, label='Role')

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'middle_name', 'role', 'is_active')
        labels = {'middle_name': 'Middle name (optional)', 'is_active': 'Active (can log in)'}
