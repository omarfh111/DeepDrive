from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Review URLs
    path('', views.reviews_list, name='list'),
    path('add/', views.add_review, name='add'),
    path('<int:pk>/', views.review_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_review, name='edit'),
    path('<int:pk>/delete/', views.delete_review, name='delete'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    
    # Comment URLs
    path('comment/<int:pk>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    
    # Backoffice URLs (Admin only)
    path('backoffice/', views.backoffice_dashboard, name='reviews_dashboard'),
    path('backoffice/reviews/', views.backoffice_reviews_list, name='reviews_backreviews_list'),
    path('backoffice/review/<int:pk>/', views.backoffice_review_detail, name='backoffice_review_detail'),
    path('backoffice/commentaires/', views.backoffice_commentaires_list, name='reviews_commentaires_list'),
    path('backoffice/commentaire/<int:pk>/', views.backoffice_commentaire_detail, name='backoffice_commentaire_detail'),
]