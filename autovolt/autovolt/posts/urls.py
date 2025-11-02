from django.urls import path
from . import views

urlpatterns = [
    path('portfolio-2/', views.portfolio, name='portfolio'),
    path('add-car/', views.add_car, name='cart'),  # 👈 matches your {% url 'cart' %}
]
