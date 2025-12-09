# advisor/views.py

import json
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .services import analyze_image_and_chat
from .vision.icons_api import detect_dashboard_icons   # ⚠️ important


@csrf_exempt
def advisor_chat(request):
    """
    Vue de chat principale : vue extérieure + (optionnel) tableau de bord.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée (POST uniquement)."}, status=405)

    image_file = request.FILES.get("image")  # vue principale
    if image_file is None:
        return JsonResponse({"error": "image requise au premier appel"}, status=400)

    # 🟡 tableau de bord optionnel (2e input dans ta sidebar)
    image_dashboard = request.FILES.get("image_dashboard")

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

    # 1) si on a une image de tableau de bord -> on détecte les voyants
    icons = None
    if image_dashboard:
        try:
            icons = detect_dashboard_icons(image_dashboard)
        except Exception as e:
            # on log mais on ne casse pas l'assistant
            traceback.print_exc()
            icons = None

    # 2) appel du service avec les voyants éventuellement présents + image compteur
    try:
        answer, damage_info, brand_info = analyze_image_and_chat(
            image_file=image_file,
            user_messages=messages,
            extra_data=extra,
            icons=icons,                      # 🔹 voyants
            dashboard_image_file=image_dashboard,  # 🔹 nouvelle intégration km (peut être None)
        )
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Error(s) in Vision/LLM: {e}"}, status=500)

    return JsonResponse({
        "answer": answer,
        "damage": damage_info,
        "brand": brand_info,
        "icons": icons,
        # 🔹 si tu veux exploiter le km lu automatiquement côté front :
        "mileage_ai": extra.get("mileage_ai"),
        "mileage_ai_confidence": extra.get("mileage_ai_confidence"),
    })


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
