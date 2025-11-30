from django.contrib import admin
from .models import Voiture
@admin.register(Voiture)
class VoitureAdmin(admin.ModelAdmin):
    list_display = ("marque","modele","annee","prix","created_at")
# Register your models here.
