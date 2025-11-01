from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ("user", "User"),
        ("partenaire", "Partenaire"),
        ("admin", "Admin"),
    )

    user_id    = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name  = models.CharField(max_length=150, blank=True)
    email      = models.EmailField(unique=True)

    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    is_active  = models.BooleanField(default=True)
    # Needed to access Django admin; leave False for normal users.
    is_staff   = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)  # account creation date

    objects = CustomUserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]  # used by createsuperuser

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]
