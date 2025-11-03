

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

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
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('user_app:admin_user_list')

    obj.delete()
    messages.success(request, "Utilisateur supprimé avec succès.")
    return redirect('admin_user_list')