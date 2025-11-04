from django.urls import path
from .views import partenariat_create_view, partenariat_success_view  # ← relative import
from .views import *
from .views import admin_hub
from . import views
app_name = "deals"

urlpatterns = [
    path("partenariats/nouveau/", partenariat_create_view, name="partenariat_create"),
    path("partenariats/success/", partenariat_success_view, name="partenariat_success"),
    path("back/partenariats/", admin_partenariats_list, name="admin_partenariats_list"),
    path("back/partenariats/<int:pk>/approve/", admin_partenariat_approve, name="admin_partenariat_approve"),
    path("back/partenariats/<int:pk>/reject/", admin_partenariat_reject, name="admin_partenariat_reject"),
    path("back/partenariats/<int:pk>/edit/", admin_partenariat_update, name="admin_partenariat_update"),
    path("back/partenariats/<int:pk>/delete/", admin_partenariat_delete, name="admin_partenariat_delete"),
    path("back/", admin_hub, name="admin_hub"),
    
    #Marche
    path("marches/nouveau/<int:voiture_id>/", views.marche_create, name="marche_create"),
    path("marches/<int:pk>/", views.marche_detail, name="marche_detail"),
    path("mes-marches/", views.mes_marches, name="mes_marches"),
    
    path("backoffice/marches/", views.admin_marches, name="admin_marches"),
    path("backoffice/marches/<int:pk>/update/", views.admin_marche_update, name="admin_marche_update"),
    path("backoffice/marches/<int:pk>/delete/", views.admin_marche_delete, name="admin_marche_delete"),
    path("backoffice/marches/<int:pk>/confirm/", views.admin_marche_confirm, name="admin_marche_confirm"),
    path("backoffice/marches/<int:pk>/cancel/", views.admin_marche_cancel, name="admin_marche_cancel"),
]
