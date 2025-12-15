from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from posts.models import Post
from .models import Achat
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Achat
from django.db import models
import json
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

@login_required
def start_purchase(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    # empêcher achat de sa propre annonce
    if post.owner_id == request.user.id:
        raise PermissionDenied("Vous ne pouvez pas acheter votre propre annonce.")

    # créer (ou réutiliser) un achat en cours pour cet utilisateur et ce post
    achat, created = Achat.objects.get_or_create(
        post=post,
        buyer=request.user,
        statut='pending',
        defaults={'price': Decimal(str(post.price))}
    )
    return redirect('achats:achat_detail', achat_id=achat.id)

@login_required
def achat_detail(request, achat_id):
    achat = get_object_or_404(Achat, pk=achat_id)
    if achat.buyer_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied
    return render(request, 'achats/achat_detail.html', {'achat': achat})


@staff_member_required
def admin_achats_list(request):
    qs = (Achat.objects
          .select_related('post', 'buyer')
          .order_by('-date_achat'))

    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '').strip()

    if q:
        qs = qs.filter(
            Q(post__marque__icontains=q) |
            Q(post__modele__icontains=q) |
            Q(buyer__email__icontains=q) |
            Q(buyer__first_name__icontains=q) |
            Q(buyer__last_name__icontains=q)
        )

    if statut:
        # allow aliases coming from UI
        aliases = {
            "validated": Achat.Status.PAID,
            "cancelled": Achat.Status.CANCELED,  # double-l -> model single-l
            "paid": Achat.Status.PAID,
            "canceled": Achat.Status.CANCELED,
            "pending": Achat.Status.PENDING,
        }
        normalized = aliases.get(statut, statut)
        if normalized in Achat.Status.values:
            qs = qs.filter(statut=normalized)

    page_obj = Paginator(qs, 15).get_page(request.GET.get('page'))

    return render(request, 'achats/achats_list.html', {
        'page_obj': page_obj,
        'q': q,
        'statut': statut,
    })


@staff_member_required
def admin_achat_detail(request, achat_id):
    achat = get_object_or_404(
        Achat.objects.select_related('post', 'buyer'),
        pk=achat_id
    )
    paiements = achat.paiements.order_by('-date_paiement')
    return render(request, 'achats/admin_achat_detail.html', {
        'achat': achat,
        'paiements': paiements,
    })


@staff_member_required
def admin_achat_delete(request, achat_id):
    achat = get_object_or_404(Achat, pk=achat_id)
    if request.method == 'POST':
        achat.delete()
        messages.success(request, "Achat supprimé.")
        return redirect('achats:admin_achats_list')
    return render(request, 'achats/achat_delete.html', {'achat': achat})


@staff_member_required
def admin_achat_update_status(request, achat_id, new_status):
    achat = get_object_or_404(Achat, pk=achat_id)

    # normalize incoming status from URL/UI to model values
    aliases = {
        "validated": Achat.Status.PAID,
        "cancelled": Achat.Status.CANCELED,   # URL might use double-l
        "paid": Achat.Status.PAID,
        "canceled": Achat.Status.CANCELED,
        "pending": Achat.Status.PENDING,
    }
    normalized = aliases.get(new_status, new_status)

    # validate against TextChoices
    if normalized not in Achat.Status.values:
        messages.error(request, "Statut invalide.")
        return redirect('achats:admin_achat_detail', achat_id=achat.id)

    achat.statut = normalized
    achat.save(update_fields=['statut'])
    messages.success(request, f"Statut mis à jour : {achat.get_statut_display()}")
    return redirect('achats:admin_achat_detail', achat_id=achat.id)

#paiment


    

    #paiment
    from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
import stripe
from .models import Achat, Paiement

stripe.api_key = settings.STRIPE_SECRET_KEY



def _must_be_buyer_or_staff(user, achat: Achat) -> bool:
    return user.is_staff or (user.is_authenticated and user == achat.buyer)


@login_required
def start_payment(request, achat_id):
    achat = get_object_or_404(Achat, pk=achat_id, buyer=request.user)

    # amount in the smallest currency unit (cents)
    amount_cents = int((Decimal(achat.price).quantize(Decimal("0.01"))) * 100)

    # works in dev and prod
    domain = f"{request.scheme}://{request.get_host()}"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            success_url=(
                f"{domain}{reverse('achats:payment_success', args=[achat.id])}"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{domain}{reverse('achats:payment_cancel', args=[achat.id])}",
            customer_email=(request.user.email or None),
            metadata={
                "achat_id": str(achat.id),
                "post_id": str(achat.post_id),
                "user_id": str(request.user.id),
            },
            line_items=[{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,  # e.g. "usd"
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"{achat.post.marque} {achat.post.modele} ({achat.post.year})",
                        "images": [request.build_absolute_uri(achat.post.image.url)]
                                  if getattr(achat.post, "image", None) else [],
                    },
                },
                "quantity": 1,
            }],
        )
    except stripe.error.StripeError as e:
        messages.error(request, f"Stripe error: {getattr(e, 'user_message', None) or str(e)}")
        return redirect("achats:achat_detail", achat_id=achat.id)

    # Save the session id on the Achat
    achat.stripe_session_id = session.id
    achat.save(update_fields=["stripe_session_id"])

    return redirect(session.url, code=303)

def payment_success(request, achat_id):
    achat = get_object_or_404(Achat, pk=achat_id, buyer=request.user)
    achat.statut = Achat.Status.PAID         
    achat.save(update_fields=["statut"])
    messages.success(request, "Paiement réussi. Merci !")
    return redirect("posts:portfolio")


@login_required
def payment_cancel(request, achat_id):
    # Optionally persist status:
    # achat = get_object_or_404(Achat, pk=achat_id, buyer=request.user)
    # achat.statut = Achat.Status.CANCELED
    # achat.save(update_fields=["statut"])
    messages.warning(request, "Le paiement a été annulé.")
    return redirect("achats:achat_detail", achat_id=achat_id)



@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        if secret:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        else:
            # Dev mode: if no webhook secret set, parse the event without signature check
            event = stripe.Event.construct_from(
                json.loads(payload.decode('utf-8')), stripe.api_key
            )
    except Exception as e:
        return HttpResponseBadRequest(str(e))

    # Handle event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        achat_id = session.get('metadata', {}).get('achat_id')
        paiement_id = session.get('metadata', {}).get('paiement_id')
        if session.get('payment_status') == 'paid' and session_id and paiement_id:
            try:
                payment = Paiement.objects.get(id=paiement_id, stripe_session_id=session_id)
                payment.status = 'succeeded'
                payment.stripe_payment_intent_id = session.get('payment_intent')
                payment.save(update_fields=['status', 'stripe_payment_intent_id'])
                # mark achat validated
                achat = payment.achat
                achat.statut = 'validated'
                achat.save(update_fields=['statut'])
            except Paiement.DoesNotExist:
                pass

    elif event['type'] == 'payment_intent.payment_failed':
        pi = event['data']['object']
        payment = Paiement.objects.filter(stripe_payment_intent_id=pi.get('id')).first()
        if payment:
            payment.status = 'failed'
            payment.save(update_fields=['status'])

    return HttpResponse(status=200)


