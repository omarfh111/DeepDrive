from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Review URLs
    path('', views.reviews_list, name='list'),
    path('add/', views.add_review, name='add'),
    path('add/<int:car_id>/', views.add_review, name='add_for_car'),
    path('<int:pk>/', views.review_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_review, name='edit'),
    path('<int:pk>/delete/', views.delete_review, name='delete'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    
    # Comment URLs
    path('comment/<int:pk>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
]