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
from .forms import ServiceForm , AdminServiceForm 
from django.contrib.auth.decorators import login_required
from .ml.damage_detector import DamageDetector
import os
from services.ml.cost_estimator import CostEstimator
 
def service_list(request):
    """Vue principale frontend"""
    if request.method == "POST":
        print("🔥 POST reçu pour ajout de service")
        form = ServiceForm(request.POST, request.FILES)
        
        if form.is_valid():
            print("✅ Formulaire valide")
            service = form.save(commit=False)
            service.client = request.user
            service.save()
            return redirect("services:service_list")
        else:
            print("❌ Erreurs dans le formulaire:")
            print(form.errors)
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
            return redirect("services:service_list")
        else:
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


# @staff_member_required
# def admin_service_create(request):
#     """Créer un service (backoffice)"""
#     if request.method == "POST":
#         form = ServiceForm(request.POST, request.FILES)
#         if form.is_valid():
#             service = form.save()
#             return redirect("services:admin_service_list")
#     else:
#         form = ServiceForm()
    
#     return render(request, "service/admin_form.html", {
#         "form": form,
#         "title": "Ajouter un service",
#         "action": "create"
#     })




@staff_member_required
def admin_service_create(request):
    """Créer un service (backoffice)"""
    if request.method == "POST":
        form = AdminServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save()
            messages.success(request, f"✅ Service '{service.nom_service}' créé avec succès!")
            return redirect("services:admin_service_list")
        else:
            messages.error(request, "❌ Erreur lors de la création du service. Vérifiez les champs.")
    else:
        form = AdminServiceForm()
    
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
        # form = ServiceForm(request.POST, request.FILES, instance=service)
        form = AdminServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            return redirect("services:admin_service_list")
    else:
        # form = ServiceForm(instance=service)
        form = AdminServiceForm(instance=service)
    
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

@login_required
def service_create_with_ai(request):
    """Créer un service avec analyse IA"""
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        
        if form.is_valid():
            service = form.save(commit=False)
            service.client = request.user
            service.save()
            
            # Si une image est uploadée, analyser avec l'IA
            if service.image:
                try:
                    detector = DamageDetector()
                    
                    image_path = service.image.path
                    results = detector.detect(image_path, conf_threshold=0.25)
                    
                    annotated_filename = f"annotated_{os.path.basename(image_path)}"
                    annotated_path = os.path.join(
                        'media',
                        'damage_analysis',
                        annotated_filename
                    )
                    
                    os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
                    
                    detector.annotate_image(
                        image_path,
                        annotated_path,
                        detection_results=results
                    )
                    
                    cost_estimation = detector.estimate_cost(results['damages'])
                    
                    service.ai_analysis = {
                        'detection': results,
                        'cost_estimation': cost_estimation
                    }
                    service.annotated_image = f"damage_analysis/{annotated_filename}"
                    service.ai_confidence = results['avg_confidence']
                    service.is_ai_predicted = True
                    service.save()
                    
                    messages.success(
                        request,
                        f"Service créé ! {results['total_damages']} dommage(s) détecté(s)."
                    )
                    
                    return redirect('services:damage_analysis', pk=service.pk)
                    
                except Exception as e:
                    messages.error(request, f"Erreur IA : {str(e)}")
                    return redirect('services:service_list')
            else:
                messages.success(request, 'Service créé avec succès !')
                return redirect('services:service_list')
    else:
        form = ServiceForm()
    
    return render(request, 'service/service.html', {'form': form})


@login_required
def damage_analysis(request, pk):
    """Affiche les résultats de l'analyse IA"""
    
    service = get_object_or_404(Service, pk=pk)
    if not request.user.is_staff and service.client != request.user:
        messages.error(request, "Vous n'avez pas accès à ce service.")
        return redirect('services:service_list')
    
    if not service.is_ai_predicted:
        messages.warning(request, 'Ce service n\'a pas été analysé par l\'IA.')
        return redirect('service_detail', pk=pk)
    
    context = {
        'service': service,
        'analysis': service.ai_analysis,
    }
    
    return render(request, 'service/damage_analysis.html', context)


@login_required
def reanalyze_service(request, pk):
    """Relancer l'analyse IA"""
    
    service = get_object_or_404(Service, pk=pk)
    
    # Vérifier que l'utilisateur a le droit
    if not request.user.is_staff and service.client != request.user:
        messages.error(request, "Vous n'avez pas accès à ce service.")
        return redirect('services:service_list')
    
    if not service.image:
        messages.error(request, 'Aucune image à analyser.')
        return redirect('services:damage_analysis', pk=pk)  # ← CHANGE ICI
    
    try:
        detector = DamageDetector()
        
        image_path = service.image.path
        results = detector.detect(image_path, conf_threshold=0.25)
        
        annotated_filename = f"annotated_{os.path.basename(image_path)}"
        annotated_path = os.path.join(
            'media',
            'damage_analysis',
            annotated_filename
        )
        
        os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
        
        detector.annotate_image(
            image_path,
            annotated_path,
            detection_results=results
        )
        
        cost_estimation = detector.estimate_cost(results['damages'])
        
        service.ai_analysis = {
            'detection': results,
            'cost_estimation': cost_estimation
        }
        service.annotated_image = f"damage_analysis/{annotated_filename}"
        service.ai_confidence = results['avg_confidence']
        service.is_ai_predicted = True
        service.save()
        
        messages.success(
            request,
            f"Analyse mise à jour ! {results['total_damages']} dommage(s)."
        )
        
        return redirect('services:damage_analysis', pk=service.pk)
        
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")
        return redirect('services:damage_analysis', pk=pk) 
    

@staff_member_required
def admin_damage_analysis(request, pk):
    """
    Affiche les résultats de l'analyse IA pour l'admin (backoffice)
    """
    service = get_object_or_404(Service, pk=pk)
    
    # Extraire les données d'analyse
    if service.is_ai_predicted and service.ai_analysis:
        analysis = service.ai_analysis
    else:
        analysis = None
    
    context = {
        'service': service,
        'analysis': analysis
    }
    
    return render(request, 'service/admin_damage_analysis.html', context)
