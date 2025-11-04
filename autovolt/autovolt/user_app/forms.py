from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-control w-100"}),
        required=False,
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-control w-100"}),
        required=False,
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "is_active", "is_staff"]
        widgets = {
            "email":      forms.EmailInput(attrs={"class": "form-control w-100"}),
            "first_name": forms.TextInput(attrs={"class": "form-control w-100"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control w-100"}),
            "role":       forms.Select(attrs={"class": "form-select w-100"}),
            "is_active":  forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff":   forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
        if commit:
            user.save()
        return user


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            # Optional placeholders:
            placeholders = {
                "first_name": "Enter your first name",
                "last_name": "Enter your last name",
                "email": "Enter your email",
                "password1": "Enter your password",
                "password2": "Confirm your password",
            }
            if name in placeholders:
                field.widget.attrs.setdefault("placeholder", placeholders[name])
        
    class Meta:
        model  = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "client"               
        user.is_active = True              
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user