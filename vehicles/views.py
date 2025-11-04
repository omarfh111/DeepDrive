from django.shortcuts import render
from .models import Voiture
def liste_voitures(request):
    voitures = Voiture.objects.all().order_by('-created_at')
    return render(request, 'vehicles/voiture_list.html', {'voitures': voitures})
# Create your views here.
