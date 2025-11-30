from django.urls import path
from . import views

app_name = 'achats'

urlpatterns = [
    # Front purchase flow already present:
    path('start/<int:post_id>/', views.start_purchase, name='start_purchase'),
    path('<int:achat_id>/', views.achat_detail, name='achat_detail'),

    # Payments
   # achats/urls.py
    path("<int:achat_id>/pay/", views.start_payment, name="start_payment"),
    path("<int:achat_id>/pay/success/", views.payment_success, name="payment_success"),
    path("<int:achat_id>/pay/cancel/", views.payment_cancel, name="payment_cancel"),

    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),

    # Backoffice (already set)
    path('back/', views.admin_achats_list, name='admin_achats_list'),
    path('back/<int:achat_id>/', views.admin_achat_detail, name='admin_achat_detail'),
    path('back/<int:achat_id>/status/<str:new_status>/', views.admin_achat_update_status, name='admin_achat_update_status'),
    path('back/<int:achat_id>/delete/', views.admin_achat_delete, name='admin_achat_delete'),
]
