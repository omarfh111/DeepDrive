from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from datetime import datetime
from .models import Service
from .forms import ServiceForm



# ============================================
# FRONTEND VIEWS - CRUD COMPLET
# ============================================

def service_list(request):
    """Vue principale frontend"""
    if request.method == "POST":
        print("🔥 POST reçu pour ajout de service")
        form = ServiceForm(request.POST, request.FILES)
        
        if form.is_valid():
            print("✅ Formulaire valide")
            service = form.save()
            print(f"✅ Service créé : {service.nom_service}")
            messages.success(request, f"✅ Service '{service.nom_service}' ajouté avec succès !")
            return redirect("services:service_list")
        else:
            print("❌ Erreurs dans le formulaire:")
            print(form.errors)
            messages.error(request, "❌ Erreur lors de l'ajout. Vérifiez les champs.")
    else:
        form = ServiceForm()
    
    services = Service.objects.all().order_by('-date_service')
    print(f"📊 Nombre de services dans la DB : {services.count()}")
    
    paginator = Paginator(services, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'services': page_obj.object_list,
        'total_services': Service.objects.count(),
    }
    
    print(f"📄 Services envoyés au template : {page_obj.object_list.count()}")
    return render(request, "service/service.html", context)


def service_update(request, pk):
    """Modification d'un service"""
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == "POST":
        print(f"🔄 POST reçu pour modification du service {pk}")
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            print(f"✅ Service {pk} modifié")
            messages.success(request, f"✅ Service '{service.nom_service}' modifié avec succès !")
            return redirect("services:service_list")
        else:
            print(f"❌ Erreurs modification : {form.errors}")
            messages.error(request, "❌ Erreur lors de la modification.")
            return redirect("services:service_list")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print(f"📤 Envoi des données du service {pk} en JSON")
        return JsonResponse({
            'id': service.id,
            'nom_service': service.nom_service,
            'type_service': service.type_service,
            'date_service': service.date_service.strftime('%Y-%m-%d'),
            'statut': service.statut,
            'garantie': service.garantie,
            'type_vidange': service.type_vidange or '',
            'description': service.description,
            'image_url': service.image.url if service.image else '',
        })
    
    return redirect("services:service_list")


@require_POST
def service_delete(request, pk):
    """Suppression d'un service"""
    service = get_object_or_404(Service, pk=pk)
    nom = service.nom_service
    print(f"🗑️ Suppression du service {pk} : {nom}")
    service.delete()
    messages.success(request, f"🗑️ Service '{nom}' supprimé avec succès !")
    return redirect("services:service_list")


# ============================================
# BACKOFFICE VIEWS
# ============================================

@staff_member_required
def admin_hub(request):
    """Dashboard backoffice"""
    ctx = {
        "total_services": Service.objects.count(),
        "en_attente_count": Service.objects.filter(statut='En attente').count(),
        "en_cours_count": Service.objects.filter(statut='En cours').count(),
        "termines_count": Service.objects.filter(statut='Terminé').count(),
        "recent_services": Service.objects.all().order_by("-date_service")[:5],
    }
    return render(request, "service/admin_dashboard.html", ctx)


@staff_member_required
def admin_service_list(request):
    """Liste complète backoffice avec filtres"""
    qs = Service.objects.all().order_by("-date_service", "-id")

    status = request.GET.get("status")
    q = request.GET.get("q")
    
    if status in {'En attente', 'En cours', 'Terminé', 'Annulé'}:
        qs = qs.filter(statut=status)
    if q:
        qs = qs.filter(nom_service__icontains=q) | qs.filter(type_service__icontains=q) | qs.filter(description__icontains=q)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "service/admin_list.html", {
        "page_obj": page_obj,
        "status": status or "",
        "q": q or "",
        "statuts": [
            ('En attente', 'En attente'),
            ('En cours', 'En cours'),
            ('Terminé', 'Terminé'),
            ('Annulé', 'Annulé')
        ],
    })


@staff_member_required
def admin_service_create(request):
    """Créer un service (backoffice)"""
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save()
            messages.success(request, f"✅ Service '{service.nom_service}' créé avec succès.")
            return redirect("services:admin_service_list")
    else:
        form = ServiceForm()
    
    return render(request, "service/admin_form.html", {
        "form": form,
        "title": "Ajouter un service",
        "action": "create"
    })


@staff_member_required
def admin_service_update(request, pk):
    """Modifier un service (backoffice)"""
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Service '{service.nom_service}' mis à jour.")
            return redirect("services:admin_service_list")
    else:
        form = ServiceForm(instance=service)
    
    return render(request, "service/admin_form.html", {
        "form": form,
        "title": f"Modifier : {service.nom_service}",
        "action": "update",
        "service": service
    })


@staff_member_required
def admin_service_delete(request, pk):
    """Confirmation de suppression (backoffice)"""
    service = get_object_or_404(Service, pk=pk)
    
    if request.method == "POST":
        nom = service.nom_service
        service.delete()
        messages.success(request, f"🗑️ Service '{nom}' supprimé.")
        return redirect("services:admin_service_list")
    
    return render(request, "service/admin_confirm_delete.html", {
        "service": service
    })


@staff_member_required
def export_services_pdf(request):
    """Export des services en PDF"""
    # Filtres (même logique que la liste)
    qs = Service.objects.all().order_by("-date_service")
    status = request.GET.get("status")
    q = request.GET.get("q")
    
    if status in {'En attente', 'En cours', 'Terminé', 'Annulé'}:
        qs = qs.filter(statut=status)
    if q:
        qs = qs.filter(nom_service__icontains=q)
    
    # Création du PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="services_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    # Configuration du document
    doc = SimpleDocTemplate(response, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Conteneur pour les éléments
    elements = []
    styles = getSampleStyleSheet()
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#DC2626'),
        spaceAfter=30,
        alignment=1  # Centré
    )
    
    # Titre
    title = Paragraph("📋 Liste des Services Automobiles", title_style)
    elements.append(title)
    
    # Informations générales
    info_style = styles['Normal']
    info_text = f"""
    <b>Date d'export :</b> {datetime.now().strftime("%d/%m/%Y à %H:%M")}<br/>
    <b>Nombre de services :</b> {qs.count()}<br/>
    <b>Filtre statut :</b> {status if status else "Tous"}
    """
    elements.append(Paragraph(info_text, info_style))
    elements.append(Spacer(1, 20))
    
    # Données du tableau
    data = [['Nom', 'Type', 'Date', 'Statut', 'Garantie']]
    
    for service in qs:
        data.append([
            Paragraph(service.nom_service[:30], styles['Normal']),
            service.type_service,
            service.date_service.strftime("%d/%m/%Y"),
            service.statut,
            service.garantie
        ])
    
    # Création du tableau
    table = Table(data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    
    # Style du tableau
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Corps du tableau
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    
    # Pied de page
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1
    )
    footer = Paragraph("Deep Drive - Système de Gestion des Services", footer_style)
    elements.append(footer)
    
    # Construction du PDF
    doc.build(elements)
    
    return response