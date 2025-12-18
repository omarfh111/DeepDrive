from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import Voiture

def liste_voitures(request):
    qs = Voiture.objects.all().order_by("-created_at")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(marque__icontains=q) | Q(modele__icontains=q))

    energies = request.GET.getlist("energy")
    if energies:
        qs = qs.filter(energy__in=energies)

    carrosseries = request.GET.getlist("carrosserie")
    if carrosseries:
        qs = qs.filter(carrosserie__in=carrosseries)

    min_price = request.GET.get("min_price") or None
    max_price = request.GET.get("max_price") or None
    try:
        if min_price:
            qs = qs.filter(prix__gte=Decimal(min_price))
        if max_price:
            qs = qs.filter(prix__lte=Decimal(max_price))
    except (InvalidOperation, TypeError):
        pass

    page_obj = Paginator(qs, 9).get_page(request.GET.get("page"))

    ctx = {
        "voitures": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "min_price": min_price,
        "max_price": max_price,
        "energy_choices": Voiture.ENERGY_CHOICES,
        "carrosserie_choices": Voiture.CARROSSERIE_CHOICES,
        "sel_energies": energies,
        "sel_carrosseries": carrosseries,
    }
    return render(request, "vehicles/voiture_list.html", ctx)
