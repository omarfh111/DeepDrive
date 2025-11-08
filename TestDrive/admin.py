from django.contrib import admin
from .models import TestDrive
def  mark_as_cancelled(modeladmin,req,queryset):
    queryset.update(status="cancelled")
def  mark_as_done(modeladmin,req,queryset):
    queryset.update(status="done")
@admin.register(TestDrive)
class TestDriveAdmin(admin.ModelAdmin):
    list_display = (
        'id_test_drive', 'user', 'car', 'reservation_date',
        'reservation_time', 'duration', 'status', 'test_location',
        'contact_phone', 'driver_license_number', 'created_at','no_show_history', 'reservation_count',
    )
    readonly_fields = ('id_test_drive', 'created_at', 'updated_at', 'no_show_history', 'reservation_count')

    search_fields = ('user__username', 'car__marque', 'car__modele', 'contact_phone')

    list_filter = ('status', 'test_location', 'reservation_date', 'created_at')

    fieldsets = (
        ('Informations générales', {
            'fields': ('id_test_drive', 'user', 'car', 'status')
        }),
        ('Détails de réservation', {
            'fields': (
                'reservation_date', 'reservation_time', 'duration',
                'test_location', 'comments'
            )
        }),
        ('Informations client', {
            'fields': ('contact_phone', 'driver_license_number')
        }),
        ('Statistiques automatiques', {
            'fields': ('no_show_history', 'reservation_count')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    actions =[mark_as_cancelled,mark_as_done]
