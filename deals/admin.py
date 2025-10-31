from django.contrib import admin
from .models import Partenariat

@admin.register(Partenariat)
class PartenariatAdmin(admin.ModelAdmin):
    list_display = ("id_partenariat","user","nom_societe","email","telephone","plafond","status","date_partenariat")
    list_filter = ("status",)
    search_fields = ("nom_societe","email","user__username","user__email")
