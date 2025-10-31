from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import PartenariatCreateForm
from .models import Partenariat

@login_required
def partenariat_create_view(request):
    # 🔹 Si l'utilisateur a déjà un partenariat => on affiche la fiche, pas le formulaire
    existing = getattr(request.user, "partenariat", None)
    if existing:
        return render(request, "deals/partenariat_detail.html", {"partenariat": existing})

    # 🔹 Sinon, il peut créer une nouvelle demande
    if request.method == "POST":
        form = PartenariatCreateForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.status = Partenariat.Statut.PENDING
            p.save()
            messages.success(request, "Votre demande de partenariat a été envoyée avec succès.")
            return redirect("deals:partenariat_create")  # recharge la page (maintenant en mode "fiche")
    else:
        form = PartenariatCreateForm()

    return render(request, "deals/partenariat_create.html", {"form": form})
def partenariat_success_view(request):
    return render(request, "deals/partenariat_success.html")
