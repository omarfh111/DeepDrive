from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Service
from .forms import ServiceForm

def dashboard(request):
    """Vue principale du dashboard admin avec statistiques et services récents."""
    total_services = Service.objects.count()
    services_en_cours = Service.objects.filter(statut='En cours').count()
    services_termines = Service.objects.filter(statut='Terminé').count()
    services_en_attente = Service.objects.filter(statut='En attente').count()
    
    recent_services = Service.objects.all().order_by('-date_service')[:5]
    
    context = {
        'total_services': total_services,
        'services_en_cours': services_en_cours,
        'services_termines': services_termines,
        'services_en_attente': services_en_attente,
        'recent_services': recent_services,
    }
    
    return render(request, 'backoffice/service/dashboard.html', context)  # Chemin exact pour ton fichier

def admin_service_list(request):
    """Liste tous les services dans le backoffice."""
    services = Service.objects.all().order_by('-date_service')
    context = {'services': services}
    return render(request, 'backoffice/service/list.html', context)

def admin_service_create(request):
    """Créer un nouveau service."""
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service créé avec succès !')
            return redirect('services:admin_service_list')
    else:
        form = ServiceForm()
    
    return render(request, 'backoffice/service/form.html', {
        'form': form,
        'title': 'Ajouter un service',
        'action': 'create'
    })

def admin_service_update(request, pk):
    """Modifier un service existant."""
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'Service "{service.nom_service}" modifié !')
            return redirect('services:admin_service_list')
    else:
        form = ServiceForm(instance=service)
    
    return render(request, 'backoffice/service/form.html', {
        'form': form,
        'title': f'Modifier le service : {service.nom_service}',
        'action': 'update',
        'service': service
    })

def admin_service_delete(request, pk):
    """Supprimer un service avec confirmation."""
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == 'POST':
        service.delete()
        messages.success(request, f'Service "{service.nom_service}" supprimé !')
        return redirect('services:admin_service_list')
    
    return render(request, 'backoffice/service/confirm_delete.html', {'service': service})