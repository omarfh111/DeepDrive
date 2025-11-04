from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import PartenariatCreateForm
from .models import Partenariat
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import PartenariatAdminForm

@login_required
def partenariat_create_view(request):
    # 🔹 Si l'utilisateur a déjà un partenariat => on affiche la fiche, pas le formulaire
    existing = getattr(request.user, "partenariat", None)
    if existing:
        return render(request, "deals/partenariat_success.html", {"partenariat": existing})

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


@staff_member_required
def admin_partenariats_list(request):
    qs = Partenariat.objects.select_related("user").all().order_by("-date_partenariat","-id_partenariat")

    # filtres
    status = request.GET.get("status")
    q = request.GET.get("q")
    if status in {s for s, _ in Partenariat.Statut.choices}:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(nom_societe__icontains=q) | qs.filter(email__icontains=q) | qs.filter(user__username__icontains=q)

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "deals/admin_partenariats_list.html", {
        "page_obj": page_obj,
        "status": status or "",
        "q": q or "",
        "choices": Partenariat.Statut.choices,
    })

@staff_member_required
@require_POST
def admin_partenariat_approve(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    p.approve()
    messages.success(request, f"Partenariat #{p.id_partenariat} approuvé.")
    return redirect("deals:admin_partenariats_list")

@staff_member_required
@require_POST
def admin_partenariat_reject(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    p.reject()
    messages.info(request, f"Partenariat #{p.id_partenariat} rejeté.")
    return redirect("deals:admin_partenariats_list")
@staff_member_required
def admin_partenariat_update(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    if request.method == "POST":
        form = PartenariatAdminForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, f"Partenariat #{p.id_partenariat} mis à jour.")
            return redirect("deals:admin_partenariats_list")
    else:
        form = PartenariatAdminForm(instance=p)
    return render(request, "deals/admin_partenariat_edit.html", {"form": form, "p": p})

@staff_member_required
@require_POST
def admin_partenariat_delete(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    p.delete()
    messages.success(request, f"Partenariat #{pk} supprimé.")
    return redirect("deals:admin_partenariats_list")
@staff_member_required
def admin_hub(request):
    # Si tu as une enum Statut dans le modèle
    ctx = {
        "total_partenariats": Partenariat.objects.count(),
        "pending_count": Partenariat.objects.filter(status=Partenariat.Statut.PENDING).count(),
        "approved_count": Partenariat.objects.filter(status=Partenariat.Statut.APPROVED).count(),
        "rejected_count": Partenariat.objects.filter(status=Partenariat.Statut.REJECTED).count(),
    }
    return render(request, "deals/admin_hub.html", ctx)

#Marche
# deals/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .forms import MarcheCreateForm
from .models import Partenariat, Marche
from vehicles.models import Voiture
from django.core.exceptions import PermissionDenied
def _get_partenaire_approved_or_none(user):
    if not user.is_authenticated:
        return None
    try:
        p = user.partenariat  # OneToOneField
    except Partenariat.DoesNotExist:
        return None
    return p if p.status == Partenariat.Statut.APPROVED else None

@login_required
def marche_create(request, voiture_id):
    voiture = get_object_or_404(Voiture, pk=voiture_id)
    partenaire = _get_partenaire_approved_or_none(request.user)

    form = MarcheCreateForm(request.POST or None, voiture=voiture, partenaire=partenaire)
    if request.method == "POST":
        if not partenaire:
            messages.error(request, "Votre partenariat doit être approuvé pour créer un marché.")
        elif form.is_valid():
            marche = form.save()
            messages.success(request, "Marché créé avec succès.")
            return redirect("deals:marche_detail", pk=marche.pk)  # (ou mes_marches si tu n'as pas encore la page détail)

    ctx = {
        "form": form,
        "voiture": voiture,
        "taux_rentabilite": 10,  # affichage côté front (le modèle recalculera de toute façon)
        "partenaire_approved": bool(partenaire),
    }
    return render(request, "deals/marche_form.html", ctx)
@login_required
def marche_detail(request, pk):
    marche = get_object_or_404(Marche.objects.select_related("voiture","partenaire"), pk=pk)
    # sécurité: un partenaire ne voit que ses propres marchés (staff a accès total)
    partenaire = _get_partenaire_approved_or_none(request.user)
    if not request.user.is_staff and marche.partenaire != partenaire:
        raise PermissionDenied
    return render(request, "deals/marche_detail.html", {"marche": marche})