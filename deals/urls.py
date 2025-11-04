from django.urls import path
from .views import partenariat_create_view, partenariat_success_view  # ← relative import
from .views import *
from .views import admin_hub
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
]
