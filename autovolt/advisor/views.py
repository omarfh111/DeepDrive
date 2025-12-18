import json
import traceback
import stripe
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import AdvisorAccess
from .guards import require_advisor_access

from .services import analyze_image_and_chat
from .vision.icons_api import detect_dashboard_icons
from .vision.price_model import predict_car_price

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def advisor_pay(request):
    """
    Pay page (UI shows TND, Stripe charges in STRIPE_CURRENCY).
    IMPORTANT: this renders advisor/paywall.html (so no more missing pay.html).
    """
    return render(request, "advisor/paywall.html", {
        "price_tnd": settings.ADVISOR_PRICE_TND,
        "price_usd": getattr(settings, "ADVISOR_PRICE_USD_CENTS", 2500) / 100,
        "currency": settings.STRIPE_CURRENCY.upper(),
    })


@login_required
@require_POST
def advisor_create_checkout(request):
    """
    Creates a Stripe Checkout Session for 1h advisor access.
    Charges in STRIPE_CURRENCY (usd) and shows ADVISOR_PRICE_TND on UI.
    """
    currency = settings.STRIPE_CURRENCY  # "usd"
    unit_amount = int(getattr(settings, "ADVISOR_PRICE_USD_CENTS", 2500))  # cents

    success_url = request.build_absolute_uri(reverse("advisor_checkout_success"))
    cancel_url = request.build_absolute_uri(reverse("advisor_pay"))

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {"name": "Conseiller auto IA — Accès 1 heure"},
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }],
            metadata={
                "user_id": str(request.user.id),
                "product": "advisor_1h",
            },
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
    except Exception as e:
        return HttpResponseBadRequest(str(e))

    return redirect(session.url, code=303)


@login_required
def advisor_checkout_success(request):
    """
    User returns here after payment. We verify session is paid, then grant 1h.
    """
    session_id = request.GET.get("session_id")
    if not session_id:
        return redirect("advisor_pay")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        return redirect("advisor_pay")

    if session.payment_status != "paid":
        return redirect("advisor_pay")

    # Create or extend access to 1 hour from now
    now = timezone.now()
    duration = timedelta(seconds=getattr(settings, "ADVISOR_DURATION_SECONDS", 3600))
    new_until = now + duration

    obj, created = AdvisorAccess.objects.get_or_create(
        stripe_session_id=session_id,
        defaults={"user": request.user, "active_until": new_until},
    )
    if not created:
        # If the record exists, ensure it's at least 1h from now
        if obj.active_until < new_until:
            obj.active_until = new_until
            obj.save(update_fields=["active_until"])

    return redirect("advisor_ui")


@login_required
def advisor_ui(request):
    """
    Advisor UI is only accessible if the user has an active AdvisorAccess.
    """
    ok = AdvisorAccess.objects.filter(
        user=request.user,
        active_until__gt=timezone.now()
    ).exists()

    if not ok:
        return redirect("advisor_pay")

    return render(request, "advisor/advisor_chat.html")


@csrf_exempt
@require_advisor_access
def advisor_chat(request):
    """
    Chat endpoint used by advisor_chat.html JS (POST FormData).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    image_file = request.FILES.get("image")
    if image_file is None:
        return JsonResponse({"error": "image requise au premier appel"}, status=400)

    image_dashboard = request.FILES.get("image_dashboard")
    image_engine = request.FILES.get("image_engine")

    messages_raw = request.POST.get("messages", "[]")
    extra_raw = request.POST.get("extra", "{}")

    try:
        messages = json.loads(messages_raw) if messages_raw else []
    except json.JSONDecodeError:
        messages = []

    try:
        extra = json.loads(extra_raw) if extra_raw else {}
    except json.JSONDecodeError:
        extra = {}

    icons = None
    if image_dashboard:
        try:
            icons = detect_dashboard_icons(image_dashboard)
        except Exception:
            traceback.print_exc()
            icons = None

    try:
        answer, damage_info, brand_info = analyze_image_and_chat(
            image_file=image_file,
            user_messages=messages,
            extra_data=extra,
            icons=icons,
            dashboard_image_file=image_dashboard,
            engine_image_file=image_engine,
        )
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Error(s) in Vision/LLM: {e}"}, status=500)

    price_ai = extra.get("price_ai")
    price_ai_reason = extra.get("price_ai_reason")
    try:
        price_ai_rounded = int(round(float(price_ai))) if price_ai is not None else None
    except Exception:
        price_ai_rounded = None

    return JsonResponse({
        "answer": answer,
        "damage": damage_info,
        "brand": brand_info,
        "icons": icons,

        "mileage_ai": extra.get("mileage_ai"),
        "mileage_ai_confidence": extra.get("mileage_ai_confidence"),

        "engine_parts": extra.get("engine_parts"),
        "engine_eval": extra.get("engine_eval"),

        "price_ai": price_ai,
        "price_ai_rounded": price_ai_rounded,
        "price_ai_reason": price_ai_reason,
    })


@csrf_exempt
def price_api(request):
    """
    Endpoint PRIX uniquement (sans images).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(body) if body else {}
    except Exception:
        return JsonResponse({"error": "JSON invalide."}, status=400)

    annee = data.get("annee")
    kilometrage = data.get("kilometrage")
    marque = data.get("marque")
    modele = data.get("modele")

    missing = []
    if annee is None: missing.append("annee")
    if kilometrage is None: missing.append("kilometrage")
    if not marque: missing.append("marque")
    if not modele: missing.append("modele")
    if missing:
        return JsonResponse({"error": f"Champs manquants: {', '.join(missing)}"}, status=400)

    try:
        price = predict_car_price(
            annee=int(annee),
            kilometrage=float(kilometrage),
            marque=str(marque),
            modele=str(modele),
        )
        return JsonResponse({
            "price": float(price),
            "price_rounded": int(round(float(price))),
            "inputs": {
                "annee": int(annee),
                "kilometrage": float(kilometrage),
                "marque": str(marque),
                "modele": str(modele),
            }
        })
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Erreur modèle prix: {e}"}, status=500)


@csrf_exempt
def dashboard_icons_api(request):
    """
    Endpoint séparé pour la détection de voyants (POST FormData image).
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    image_file = request.FILES.get("image")
    if image_file is None:
        return JsonResponse({"error": "Aucune image reçue"}, status=400)

    try:
        lights = detect_dashboard_icons(image_file)
        return JsonResponse({"lights": lights})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
