from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import PartenariatCreateForm
from .models import Partenariat, Marche
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import PartenariatAdminForm
from .forms import MarcheCreateForm
from vehicles.models import Voiture
from django.core.exceptions import PermissionDenied
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
    return redirect("deals:admin_partenariats_list")

@staff_member_required
@require_POST
def admin_partenariat_reject(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    p.reject()
    return redirect("deals:admin_partenariats_list")
@staff_member_required
def admin_partenariat_update(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    if request.method == "POST":
        form = PartenariatAdminForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
            return redirect("deals:admin_partenariats_list")
    else:
        form = PartenariatAdminForm(instance=p)
    return render(request, "deals/admin_partenariat_edit.html", {"form": form, "p": p})

@staff_member_required
@require_POST
def admin_partenariat_delete(request, pk):
    p = get_object_or_404(Partenariat, pk=pk)
    p.delete()
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
from .emails import send_marche_creation_email
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
            try:
                send_marche_creation_email(marche)
            except Exception as e:
                print("Erreur envoi e-mail marché :", e)

            return redirect("deals:marche_detail", pk=marche.pk)

    ctx = {
        "form": form,
        "voiture": voiture,
        "taux_rentabilite": 10,
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
@login_required
def mes_marches(request):
    partenaire = _get_partenaire_approved_or_none(request.user)
    if not partenaire:
        raise PermissionDenied("Partenaire non approuvé.")

    q = request.GET.get("q", "").strip()
    etat = request.GET.get("etat", "").strip()

    qs = (Marche.objects
          .filter(partenaire=partenaire)
          .select_related("voiture")
          .order_by("-created_at"))

    if q:
        qs = qs.filter(
            Q(voiture__marque__icontains=q) |
            Q(voiture__modele__icontains=q)
        )

    if etat:
        qs = qs.filter(etat=etat)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "etat": etat,
        "choices": Marche.ETAT_CHOICES,  # pour le <select>
    }
    return render(request, "deals/mes_marches.html", context)
@staff_member_required
def admin_marches(request):
    q = request.GET.get("q", "").strip()
    etat = request.GET.get("etat", "").strip()

    qs = (Marche.objects
          .select_related("voiture", "partenaire")
          .order_by("-created_at"))

    if q:
        qs = qs.filter(
            Q(voiture__marque__icontains=q) |
            Q(voiture__modele__icontains=q) |
            Q(partenaire__nom_societe__icontains=q)
        )
    if etat:
        qs = qs.filter(etat=etat)

    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "q": q,
        "etat": etat,
        "choices": Marche.ETAT_CHOICES,
    }
    return render(request, "deals/marche_admin_list.html", context)

@staff_member_required
def admin_marche_delete(request, pk):
    marche = get_object_or_404(Marche, pk=pk)
    if request.method == "POST":
        marche.delete()
    return redirect("deals:admin_marches")

@staff_member_required
def admin_marche_confirm(request, pk):
    marche = get_object_or_404(Marche, pk=pk)
    if request.method == "POST":
        marche.etat = "valide"
        marche.save(update_fields=["etat"])
    return redirect("deals:admin_marches")

@staff_member_required
def admin_marche_cancel(request, pk):
    marche = get_object_or_404(Marche, pk=pk)
    if request.method == "POST":
        marche.etat = "annule"
        marche.save(update_fields=["etat"])
    return redirect("deals:admin_marches")

# (optionnel) édition basique via ModelForm
from django import forms
class AdminMarcheForm(forms.ModelForm):
    class Meta:
        model = Marche
        fields = ["quantite", "taux_rentabilite", "etat"]
        widgets = {
            "quantite": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "taux_rentabilite": forms.NumberInput(attrs={"step": "0.01", "class": "form-control"}),
            "etat": forms.Select(attrs={"class": "form-select"}),
        }
@staff_member_required
def admin_marche_update(request, pk):
    marche = get_object_or_404(Marche.objects.select_related("voiture", "partenaire"), pk=pk)
    if request.method == "POST":
        form = AdminMarcheForm(request.POST, instance=marche)
        if form.is_valid():
            obj = form.save(commit=False)
            # Les recalculs (total_prix, rentabilite_estime) sont faits dans model.save()
            obj.save()
            return redirect("deals:admin_marches")
    else:
        form = AdminMarcheForm(instance=marche)
    return render(request, "deals/marche_admin_update.html", {"form": form, "marche": marche})
# PDF facture
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO

@login_required
def marche_invoice_pdf(request, pk):
    """
    Génère la facture PDF d'un marché.
    - Un partenaire ne peut télécharger QUE ses propres marchés approuvés (ou en attente, à toi de décider).
    - Le staff peut tout télécharger.
    """
    marche = get_object_or_404(Marche.objects.select_related("voiture", "partenaire"), pk=pk)

    # Sécurité: partenaire ne voit que ses marchés
    partenaire = _get_partenaire_approved_or_none(request.user)
    if not request.user.is_staff:
        if not partenaire or marche.partenaire_id != partenaire.id_partenariat:
            raise PermissionDenied

    context = {
        "marche": marche,
        "voiture": marche.voiture,
        "partenaire": marche.partenaire,
        "societe": marche.partenaire.nom_societe or "",
        "now": marche.created_at,  # date du marché (ou timezone.now() si tu veux l'instant)
    }

    html = render_to_string("deals/invoices/marche_invoice.html", context)

    # Rendu PDF
    pdf_io = BytesIO()
    pisa_status = pisa.CreatePDF(src=html, dest=pdf_io, encoding="utf-8")
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)

    pdf_io.seek(0)
    filename = f"facture-marche-{marche.id}.pdf"
    response = HttpResponse(pdf_io.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response