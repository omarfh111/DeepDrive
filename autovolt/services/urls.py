from django.urls import path
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
    # ============================================
    # FRONTEND ROUTES - CRUD Public
    # ============================================
    path("", service_list, name="service_list"),  # /service/ → Liste + Ajout
    path("<int:pk>/update/", service_update, name="service_update"),  # /service/1/update/
    path("<int:pk>/delete/", service_delete, name="service_delete"),  # /service/1/delete/
    
    # ============================================
    # BACKOFFICE ROUTES
    # ============================================
    path("admin/", admin_hub, name="admin_hub"),  # /service/admin/ → Dashboard
    path("admin/list/", admin_service_list, name="admin_service_list"),  # /service/admin/list/
    path("admin/create/", admin_service_create, name="admin_service_create"),  # /service/admin/create/
    path("admin/<int:pk>/update/", admin_service_update, name="admin_service_update"),  # /service/admin/1/update/
    path("admin/<int:pk>/delete/", admin_service_delete, name="admin_service_delete"),  # /service/admin/1/delete/
    path("admin/export-pdf/", export_services_pdf, name="export_services_pdf"),  # /service/admin/export-pdf/
]



# from django.urls import path
# from .views import service_list, service_update, service_delete

# app_name = "services"

# urlpatterns = [
#     # ============================================
#     # FRONTEND ROUTES - CRUD Public
#     # ============================================
#     path("", service_list, name="service_list"),  # /service/ → Liste + Ajout
#     path("<int:pk>/update/", service_update, name="service_update"),  # /service/1/update/
#     path("<int:pk>/delete/", service_delete, name="service_delete"),  # /service/1/delete/
# ]
