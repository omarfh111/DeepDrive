from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import RoleBasedLoginView


urlpatterns = [
    path('back/users/', views.admin_user_list, name='admin_user_list'),
    path('back/users/edit/<int:pk>/', views.admin_user_edit, name='admin_user_edit'),
    path('back/users/delete/<int:pk>/', views.admin_user_delete, name='admin_user_delete'),
    path("auth/register/", views.register, name="register"),
    path("auth/login/", RoleBasedLoginView.as_view(), name="login"),
]