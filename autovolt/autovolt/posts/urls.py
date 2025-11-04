from django.urls import path
from . import views

urlpatterns = [
    path('portfolio-2/', views.portfolio, name='portfolio'),
    path('update/<int:post_id>/', views.update_post, name='update_post'),  # 👈 NEW
    path('add-car/', views.add_car, name='cart'),  # 👈 matches your {% url 'cart' %}
    path('cars/<int:pk>/delete/', views.delete_car, name='delete_car'),

]
