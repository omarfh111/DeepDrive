from django.contrib import admin
from .models import Partenariat, Marche
from django.http import HttpResponse
import csv

#@admin.register(Partenariat)
#class PartenariatAdmin(admin.ModelAdmin):
    #list_display = ("id_partenariat","user","nom_societe","email","telephone","plafond","status","date_partenariat")
    #list_filter = ("status",)
   # search_fields = ("nom_societe","email","user__username","user__email")

@admin.action(description="Approuver")
def action_approve(modeladmin, request, queryset):
    queryset.update(status=Partenariat.Statut.APPROVED)

@admin.action(description="Rejeter")
def action_reject(modeladmin, request, queryset):
    queryset.update(status=Partenariat.Statut.REJECTED)

@admin.action(description="Exporter CSV")
def action_export_csv(modeladmin, request, queryset):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="partenariats.csv"'
    w = csv.writer(resp)
    w.writerow(["ID","User","Société","Email","Téléphone","CEO","Date","Plafond","Statut"])
    for p in queryset.select_related("user"):
        w.writerow([p.pk, getattr(p.user, "username", ""), p.nom_societe or "", p.email or "",
                    p.telephone or "", p.nom_ceo or "", p.date_partenariat or "",
                    p.plafond or "", p.status])
    return resp

@admin.register(Partenariat)   # 👈 UNE SEULE inscription ici
class PartenariatAdmin(admin.ModelAdmin):
    list_display = ("id_partenariat","user","nom_societe","email","telephone",
                    "nom_ceo","date_partenariat","plafond","status")
    list_filter = ("status","date_partenariat")
    search_fields = ("nom_societe","email","telephone","nom_ceo","user__username","user__email")
    ordering = ("-date_partenariat","-id_partenariat")
    date_hierarchy = "date_partenariat"
    actions = [action_approve, action_reject, action_export_csv]

# ❌ Ne PAS remettre admin.site.register(Partenariat, PartenariatAdmin)
#Marche 
@admin.register(Marche)
class MarcheAdmin(admin.ModelAdmin):
    list_display = (
        "id", "partenaire", "voiture", "quantite",
        "prix_unitaire", "total_prix", "taux_rentabilite",
        "rentabilite_estime", "etat", "created_at",
    )
    list_filter = ("etat", "created_at", "partenaire__status")
    search_fields = ("partenaire__nom_societe", "voiture__marque", "voiture__modele")
