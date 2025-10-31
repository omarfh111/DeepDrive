from django.urls import path
from .views import partenariat_create_view, partenariat_success_view  # ← relative import

app_name = "deals"

urlpatterns = [
    path("partenariats/nouveau/", partenariat_create_view, name="partenariat_create"),
    path("partenariats/success/", partenariat_success_view, name="partenariat_success"),
]
