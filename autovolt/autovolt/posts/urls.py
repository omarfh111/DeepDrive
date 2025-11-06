from django.urls import path
from . import views


urlpatterns = [
    # Frontend
    path('portfolio-2/', views.portfolio, name='portfolio'),
    path('add-car/', views.add_car, name='cart'),
    path('update/<int:post_id>/', views.update_post, name='update_post'),
    path('cars/<int:pk>/delete/', views.delete_car, name='delete_car'),

    # Backoffice
    path('back/', lambda request: views.portfolio(request, backoffice=True), name='admin_portfolio'),
    path('back/add/', lambda request: views.add_car(request, backoffice=True), name='admin_add_car'),
    path('back/update/<int:post_id>/', lambda request, post_id: views.update_post(request, post_id, backoffice=True), name='admin_update_post'),
    path('back/delete/<int:pk>/', lambda request, pk: views.delete_car(request, pk, backoffice=True), name='admin_delete_car'),
]
