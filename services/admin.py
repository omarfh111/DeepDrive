from django.contrib import admin
from .models import Service
from django.http import HttpResponse
import csv

@admin.action(description="Marquer comme terminé")
def action_terminate(modeladmin, request, queryset):
    queryset.update(statut='Terminé')

@admin.action(description="Exporter CSV")
def action_export_csv(modeladmin, request, queryset):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="services.csv"'
    w = csv.writer(resp)
    w.writerow(["ID", "Nom", "Type", "Statut", "Date", "Garantie"])
    for s in queryset.all():
        w.writerow([s.pk, s.nom_service, s.type_service, s.statut, s.date_service, s.garantie])
    return resp

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("nom_service", "type_service", "statut", "date_service", "garantie")
    list_filter = ("statut", "type_service", "date_service")
    search_fields = ("nom_service", "description", "type_service")
    ordering = ("-date_service",)
    actions = [action_terminate, action_export_csv]