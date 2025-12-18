from django.urls import path
from . import views 
from .views import (
    service_list, 
    service_update, 
    service_delete,
    admin_hub,
    admin_service_list,
    admin_service_create,
    admin_service_update,
    admin_service_delete,
    export_services_pdf
 )

app_name = "services"

urlpatterns = [
    # FRONTEND ROUTES - CRUD Public
   
    path("", service_list, name="service_list"),  # /service/ → Liste + Ajout
    path("<int:pk>/update/", service_update, name="service_update"),  # /service/1/update/
    path("<int:pk>/delete/", service_delete, name="service_delete"),  # /service/1/delete/
     # ============================================
    # BACKOFFICE ROUTES
    # ============================================
    path("back/admin/", admin_hub, name="admin_hub"),  # /service/admin/ → Dashboard
    path("back/admin/list/", admin_service_list, name="admin_service_list"),  # /service/admin/list/
    path("back/admin/create/", admin_service_create, name="admin_service_create"),  # /service/admin/create/
    path("back/admin/<int:pk>/update/", admin_service_update, name="admin_service_update"),  # /service/admin/1/update/
    path("back/admin/<int:pk>/delete/", admin_service_delete, name="admin_service_delete"),  # /service/admin/1/delete/
    path("back/admin/export-pdf/", export_services_pdf, name="export_services_pdf"),  # /service/admin/export-pdf/
    path('create-ai/', views.service_create_with_ai, name='service_create_ai'),
    path('damage-analysis/<int:pk>/', views.damage_analysis, name='damage_analysis'),
    path('reanalyze/<int:pk>/', views.reanalyze_service, name='reanalyze_service'),
    path('back/admin/<int:pk>/analysis/', views.admin_damage_analysis, name='admin_damage_analysis'),

]
