from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    path("voitures/", views.liste_voitures, name="liste_voitures"),
]