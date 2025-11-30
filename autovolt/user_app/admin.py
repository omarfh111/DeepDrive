from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model  = User
        fields = ("email", "first_name", "last_name", "role")

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ("email", "first_name", "last_name", "role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")


class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form     = UserChangeForm
    model    = User

    list_display = ("id", "email", "first_name", "last_name", "role", "is_active", "is_staff", "date_joined")
    list_filter  = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2", "is_active", "is_staff"),
        }),
    )

admin.site.register(User, UserAdmin)
