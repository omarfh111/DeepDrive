# services/emails.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_service_status_email(service):
    """
    Envoie un email au client quand le statut du service devient 'Terminé' ou 'Annulé'.
    Envoie également une copie en BCC aux administrateurs.
    """
    # Vérifier qu'il y a un client avec un email
    if not service.client or not service.client.email:
        return

    context = {
        "client_name": service.client.first_name or service.client.email.split('@')[0],
        "nom_service": service.nom_service,
        "type_service": service.type_service,
        "date_service": service.date_service,
        "statut": service.statut,
        "description": service.description,
        "garantie": service.garantie,
        "service_id": service.id,
    }

    # Choisir le template selon le statut
    if service.statut == 'Terminé':
        subject = "✅ Votre service a été terminé"
        txt_template = "service/emails/service_completed.txt"
        html_template = "service/emails/service_completed.html"
    elif service.statut == 'Annulé':
        subject = "❌ Votre service a été annulé"
        txt_template = "service/emails/service_cancelled.txt"
        html_template = "service/emails/service_cancelled.html"
    else:
        return

    # Générer les contenus texte et HTML
    text_body = render_to_string(txt_template, context)
    html_body = render_to_string(html_template, context)

    # Récupérer la liste des emails administrateurs
    admin_emails = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", [])

    # Créer et envoyer l'email
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[service.client.email],
        bcc=admin_emails,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)