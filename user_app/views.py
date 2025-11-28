

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

def admin_dashboard(request):
    return render(request, 'admin_themes/index.html')

def admin_user_list(request):                     
    User = get_user_model()
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'user_app/admin_user_list.html', {'users': users})


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