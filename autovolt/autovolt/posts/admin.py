from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('marque', 'modele', 'year', 'price', 'energy', 'boite_vitesse')
    search_fields = ('marque', 'modele')
    list_filter = ('energy', 'boite_vitesse', 'etat_general', 'transmission')
