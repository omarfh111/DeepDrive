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
def admin_hub(request):
    return render(request, "deals/admin_hub.html")