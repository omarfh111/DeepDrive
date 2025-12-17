# advisor/urls.py

from django.urls import path

from .views import (
    advisor_chat,
    advisor_ui,
    dashboard_icons_api,
    price_api,          # ✅ NEW
)

urlpatterns = [
    path("chat/", advisor_chat, name="advisor_chat"),

    path("ui/", advisor_ui, name="advisor_ui"),


    path("icons/", dashboard_icons_api, name="advisor_icons"),

    path("price/", price_api, name="advisor_price"),
]
