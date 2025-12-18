from django.urls import path
from .views import (
    advisor_ui,
    advisor_chat,
    dashboard_icons_api,
    price_api,
    advisor_pay,
    advisor_create_checkout,
    advisor_checkout_success,
)

urlpatterns = [
    path("ui/", advisor_ui, name="advisor_ui"),
    path("chat/", advisor_chat, name="advisor_chat"),
    path("icons/", dashboard_icons_api, name="advisor_icons"),
    path("price/", price_api, name="advisor_price"),

    path("pay/", advisor_pay, name="advisor_pay"),
    path("checkout/create/", advisor_create_checkout, name="advisor_create_checkout"),
    path("checkout/success/", advisor_checkout_success, name="advisor_checkout_success"),
]
