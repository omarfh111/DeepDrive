from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    exclude = ("embedding",)
    list_display = ('marque', 'modele', 'year', 'price', 'energy', 'boite_vitesse', 'image_preview')
    list_display_links = ('marque', 'modele')
    search_fields = ('marque', 'modele', 'gouvernerat', 'carrosserie')
    list_filter = ('energy', 'boite_vitesse', 'etat_general', 'transmission', 'marque', 'year')
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Infos véhicule', {
            'fields': ('marque', 'modele', 'year', 'kilometrage', 'carrosserie', 'etat_general', 'nb_proprietes', 'gouvernerat')
        }),
        ('Caractéristiques', {
            'fields': ('energy', 'boite_vitesse', 'puissance_fiscale', 'transmission')
        }),
        ('Tarification & Image', {
            'fields': ('price', 'image', 'image_preview')
        }),
    )
