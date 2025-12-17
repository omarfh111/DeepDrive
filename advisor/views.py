# advisor/views.py

import json
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .services import analyze_image_and_chat
from .vision.icons_api import detect_dashboard_icons  # ⚠️ important

# (optionnel) tu peux laisser price_api utiliser predict_car_price
from .vision.price_model import predict_car_price


@csrf_exempt
def advisor_chat(request):
    """
    Vue de chat principale : vue extérieure + (optionnel) tableau de bord + (optionnel) compartiment moteur.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    image_file = request.FILES.get("image")  # vue principale
    if image_file is None:
        return JsonResponse({"error": "image requise au premier appel"}, status=400)

    # optionnels
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

    # 1) voyants (si dashboard fourni)
    icons = None
    if image_dashboard:
        try:
            icons = detect_dashboard_icons(image_dashboard)
        except Exception:
            traceback.print_exc()
            icons = None

    # 2) service principal
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

    # prix IA (déjà calculé dans services.py)
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

        # km IA
        "mileage_ai": extra.get("mileage_ai"),
        "mileage_ai_confidence": extra.get("mileage_ai_confidence"),

        # moteur
        "engine_parts": extra.get("engine_parts"),
        "engine_eval": extra.get("engine_eval"),

        # prix
        "price_ai": price_ai,
        "price_ai_rounded": price_ai_rounded,
        "price_ai_reason": price_ai_reason,   # ✅ IMPORTANT pour comprendre pourquoi "—"
    })


@csrf_exempt
def price_api(request):
    """
    Endpoint PRIX uniquement (sans images).
    POST JSON :
    {
      "annee": 2022,
      "kilometrage": 79000,
      "marque": "KIA",
      "modele": "Rio 5p"
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    # Lecture JSON
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
    Endpoint séparé uniquement pour mettre à jour la carte 'Voyants tableau de bord'
    quand l'utilisateur choisit la photo.
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


def advisor_ui(request):
    return render(request, "advisor/advisor_chat.html")
