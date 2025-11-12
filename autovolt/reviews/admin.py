from django.contrib import admin
from .models import Review, Commentaire

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for Review model
    """
    list_display = [
        'titre',
        'user',
        'note',
        'is_approved',
        'date_review',
        'date_joined'
    ]
    list_filter = [
        'note',
        'is_approved',
        'date_review',
        'date_joined'
    ]
    search_fields = [
        'titre',
        'description',
        'user__username',
        'user__email'
    ]
    readonly_fields = [
        'date_review',
        'date_joined'
    ]
    list_editable = ['is_approved']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('user', 'titre', 'note')
        }),
        ('Contenu', {
            'fields': ('description', 'image')
        }),
        ('Statut', {
            'fields': ('is_approved',)
        }),
        ('Dates', {
            'fields': ('date_review', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    """
    Admin interface for Commentaire model
    """
    list_display = [
        'user',
        'review',
        'commentaire_preview',
        'is_approved',
        'date_commentaire'
    ]
    list_filter = [
        'is_approved',
        'date_commentaire'
    ]
    search_fields = [
        'commentaire',
        'user__username',
        'review__titre'
    ]
    readonly_fields = [
        'date_commentaire'
    ]
    list_editable = ['is_approved']
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('user', 'review')
        }),
        ('Contenu', {
            'fields': ('commentaire',)
        }),
        ('Statut', {
            'fields': ('is_approved',)
        }),
        ('Dates', {
            'fields': ('date_commentaire',),
            'classes': ('collapse',)
        }),
    )
    
    def commentaire_preview(self, obj):
        """Show first 50 characters of comment"""
        return obj.commentaire[:50] + '...' if len(obj.commentaire) > 50 else obj.commentaire
    commentaire_preview.short_description = 'Aperçu'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'review')