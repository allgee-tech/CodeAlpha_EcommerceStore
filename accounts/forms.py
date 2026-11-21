from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomerProfile

User = get_user_model()

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "password1", "password2")
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or email", max_length=254)
    def clean(self):
        identifier = self.cleaned_data.get("username", "").strip()
        password = self.cleaned_data.get("password")
        if identifier and password:
            user = User.objects.filter(email__iexact=identifier).first()
            username = user.get_username() if user else identifier
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("The username or password is incorrect.")
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    class Meta:
        model = CustomerProfile
        fields = ("first_name", "last_name", "email", "phone", "address", "city", "region", "country")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("That email address is already in use.")
        return email
    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.save(update_fields=["first_name", "last_name", "email"])
        if commit:
            profile.save()
        return profile
