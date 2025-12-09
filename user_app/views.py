

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .forms import AdminUserForm
from django.contrib.auth import login
from .forms import RegisterForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Q
import random
import time
from django.core.mail import send_mail
from django.conf import settings
def admin_dashboard(request):
    return render(request, 'admin_themes/index.html')


def admin_user_list(request):
    User = get_user_model()
    q = request.GET.get("q", "").strip()

    users = User.objects.all().order_by("-date_joined")

    if q:
        users = users.filter(email__icontains=q)

    return render(
        request,
        "user_app/admin_user_list.html",
        {
            "users": users,
            "q": q,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)   
@require_POST
def admin_user_delete(request, pk):
    User = get_user_model()
    obj = get_object_or_404(User, pk=pk)

    # safety: don't let a user delete himself
    if obj.pk == request.user.pk:
        return redirect('user_app:admin_user_list')

    obj.delete()
    return redirect('admin_user_list')

User = get_user_model()

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET", "POST"])
def admin_user_edit(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    creating = obj is None

    if request.method == "POST":
        form = AdminUserForm(request.POST, instance=obj)
        if form.is_valid():
            if obj and obj.pk == request.user.pk:
                cleaned = form.cleaned_data
                if not cleaned.get("is_active", True):
                    return render(request, "user_app/admin_user_edit.html", {"form": form, "u": obj})
                if not cleaned.get("is_staff", True):
                    return render(request, "user_app/admin_user_edit.html", {"form": form, "u": obj})
            saved = form.save()
            return redirect("user_app:admin_user_list")
    else:
        form = AdminUserForm(instance=obj)

    return render(request, "user_app/admin_user_edit.html", {"form": form, "u": obj, "creating": creating})





@require_http_methods(["GET", "POST"])
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()              
            return redirect("user_app:login") 
    else:
        form = RegisterForm()
    return render(request, "admin_themes/auth-register.html", {"form": form})


class RoleBasedLoginView(LoginView):
    template_name = "admin_themes/auth-login.html"  
    def get_success_url(self):
        user = self.request.user
        if getattr(user, "role", "") == "admin":
            return reverse_lazy("user_app:admin_user_list") 
        return "/" 
    


def password_reset(request):
    """
    Custom password reset flow:
    1) Step 'email': user enters email, if exists → send 6-digit code (valid 2 minutes).
    2) Step 'code': user enters code + new password + confirmation → reset password.
    """
    User = get_user_model()

    # Optional: show a message if redirected after expiry
    if request.GET.get("reset") == "expired":
        messages.error(request, "The verification code has expired. Please request a new one.")

    # Determine current step from session
    step = "email"
    sess_code = request.session.get("reset_code")
    sess_expires = request.session.get("reset_expires_at")

    if sess_code and sess_expires and time.time() <= sess_expires:
        step = "code"
    else:
        # Clean expired data
        for key in ["reset_email", "reset_code", "reset_expires_at"]:
            request.session.pop(key, None)

    if request.method == "POST":
        step = request.POST.get("step", "email")

        # ---------- STEP 1 : USER ENTERS EMAIL ----------
        if step == "email":
            email_value = request.POST.get("email", "").strip().lower()
            if not email_value:
                messages.error(request, "Please enter your email address.")
            else:
                try:
                    user = User.objects.get(email__iexact=email_value)
                except User.DoesNotExist:
                    messages.error(request, "This email address is not registered.")
                else:
                    # Generate 6-digit code
                    code = f"{random.randint(0, 999999):06d}"

                    # Store in session for 2 minutes (120s)
                    request.session["reset_email"] = user.email
                    request.session["reset_code"] = code
                    request.session["reset_expires_at"] = time.time() + 120  # 120 seconds

                    # Send email
                    try:
                        send_mail(
                            subject="Your password reset code",
                            message=f"Your password reset code is: {code}\nIt is valid for 2 minutes.",
                            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                        messages.success(
                            request,
                            "A verification code has been sent to your email address."
                        )
                        step = "code"
                    except Exception:
                        messages.error(
                            request,
                            "An error occurred while sending the email. Please try again later."
                        )

        # ---------- STEP 2 : USER ENTERS CODE + NEW PASSWORD ----------
        elif step == "code":
            code_input = request.POST.get("code", "").strip()
            password1 = request.POST.get("password1", "")
            password2 = request.POST.get("password2", "")

            sess_email = request.session.get("reset_email")
            sess_code = request.session.get("reset_code")
            sess_expires = request.session.get("reset_expires_at")
            now = time.time()

            if not (sess_email and sess_code and sess_expires):
                messages.error(request, "The reset process has expired. Please start again.")
                step = "email"
            elif now > sess_expires:
                messages.error(request, "The code has expired. Please request a new one.")
                step = "email"
                for key in ["reset_email", "reset_code", "reset_expires_at"]:
                    request.session.pop(key, None)
            elif code_input != sess_code:
                messages.error(request, "The verification code is incorrect.")
                step = "code"
            elif not password1:
                messages.error(request, "Please enter a new password.")
                step = "code"
            elif password1 != password2:
                messages.error(request, "Passwords do not match.")
                step = "code"
            elif len(password1) < 8:
                messages.error(request, "The password must contain at least 8 characters.")
                step = "code"
            else:
                try:
                    user = User.objects.get(email=sess_email)
                except User.DoesNotExist:
                    messages.error(request, "User not found. Please restart the process.")
                    step = "email"
                else:
                    user.set_password(password1)
                    user.save()

                    # Clean session keys
                    for key in ["reset_email", "reset_code", "reset_expires_at"]:
                        request.session.pop(key, None)

                    messages.success(request, "Your password has been reset. You can now sign in.")
                    return redirect("user_app:login")

    # Remaining seconds for the countdown (for JS)
    remaining_seconds = 0
    if step == "code":
        sess_expires = request.session.get("reset_expires_at")
        if sess_expires:
            remaining_seconds = max(int(sess_expires - time.time()), 0)

    context = {
        "step": step,
        "email_value": request.session.get("reset_email", ""),
        "remaining_seconds": remaining_seconds,
    }
    return render(request, "admin_themes/auth-password.html", context)
