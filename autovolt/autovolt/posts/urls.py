from django.urls import path
from . import views

app_name="posts"

urlpatterns = [
    # Front
    path('post/', views.portfolio, name='portfolio'),
    #path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/add/', views.add_car, name='add_car'),
    path('post/<int:post_id>/edit/', views.update_post, name='update_post'),
    path('post/<int:pk>/delete/', views.delete_car, name='delete_car'),

    # Backoffice (protégé admin)
    path('back/post/', views.admin_portfolio, name='admin_portfolio'),
    #path('back/post/<int:pk>/', views.admin_post_detail, name='admin_post_detail'),
    path('back/post/add/', views.admin_add_car, name='admin_add_car'),
    path('back/post/<int:post_id>/edit/', views.admin_update_post, name='admin_update_post'),
    path('back/post/<int:pk>/delete/', views.admin_delete_car, name='admin_delete_car'),
]
