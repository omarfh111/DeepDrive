# user_app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)   # <-- this is the ONLY registration
class UserAdmin(DjangoUserAdmin):
    list_display  = ("user_id", "email", "first_name", "last_name", "role", "is_active", "date_joined")
    ordering      = ("-date_joined",)
    search_fields = ("email", "first_name", "last_name")
    list_filter   = ("role", "is_active")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )

    readonly_fields = ("date_joined", "last_login")
