# deals/emails.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_partner_status_email(partenariat):
    """Envoie l'e-mail selon le statut courant du partenariat."""
    if not partenariat.email:
        return  # pas d'email => on ne tente rien

    context = {
        "societe": partenariat.nom_societe or "Cher partenaire",
        "user": getattr(partenariat.user, "username", None),
        "plafond": partenariat.plafond,
        "detail_societe": partenariat.detail_societe,
        "id_partenariat": partenariat.id_partenariat,
    }

    if partenariat.status == partenariat.Statut.APPROVED:
        subject = "✅ Votre partenariat a été approuvé"
        txt_template = "emails/partner_approved.txt"
        html_template = "emails/partner_approved.html"
    elif partenariat.status == partenariat.Statut.REJECTED:
        subject = "❌ Votre partenariat a été refusé"
        txt_template = "emails/partner_rejected.txt"
        html_template = "emails/partner_rejected.html"
    else:
        return  # on n'envoie rien pour 'pending'

    text_body = render_to_string(txt_template, context)
    html_body = render_to_string(html_template, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[partenariat.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)

#Marche
def send_marche_creation_email(marche):
    """
    Envoie un email de confirmation au partenaire après création d'un marché.
    """
    partenaire = marche.partenaire
    if not partenaire or not partenaire.email:
        return

    context = {
        "societe": partenaire.nom_societe or "Cher partenaire",
        "voiture": marche.voiture,
        "quantite": marche.quantite,
        "prix_unitaire": marche.prix_unitaire,
        "total_prix": marche.total_prix,
        "taux_rentabilite": marche.taux_rentabilite,
        "rentabilite_estime": marche.rentabilite_estime,
        "etat": marche.etat,
        "id_marche": marche.id,
        "date": marche.created_at,
    }

    subject = f"🧾 Nouveau marché #{marche.id} créé avec succès"
    text_body = render_to_string("emails/marche_created.txt", context)
    html_body = render_to_string("emails/marche_created.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[partenaire.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
def send_recommendation_email(partenariat, reco_data: dict):
    """
    Envoie un email avec la liste des véhicules recommandés.
    reco_data est le dict retourné par build_recommendations().
    """
    if not partenariat.email:
        return

    context = {
        "societe": partenariat.nom_societe or "Cher partenaire",
        "analysis": reco_data.get("analysis") or {},
        "recommended_vehicles": reco_data.get("recommended_vehicles") or [],
        "budget_total": reco_data.get("budget_total"),
        "total_estimated_cost": reco_data.get("total_estimated_cost"),
        "currency": reco_data.get("currency", "TND"),
    }

    subject = f"🚗 Recommandations de véhicules pour {context['societe']}"
    text_body = render_to_string("emails/partner_reco.txt", context)
    html_body = render_to_string("emails/partner_reco.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[partenariat.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)