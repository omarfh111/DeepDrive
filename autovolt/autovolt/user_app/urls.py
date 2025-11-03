from django.urls import path
from . import views

urlpatterns = [
    path('back/users/', views.admin_user_list, name='admin_user_list'),
    path('back/users/delete/<int:pk>/', views.admin_user_delete, name='admin_user_delete'),
]