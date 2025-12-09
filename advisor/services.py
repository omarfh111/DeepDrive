# advisor/services.py

from io import BytesIO

from django.conf import settings
from openai import OpenAI
from PIL import Image

from .vision.damage_model import predict_damage
from .vision.brand_model import predict_brand
from .vision.odometer_model import (
    verify_car_image,
    extract_kilometrage_from_image,
)

client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))

SYSTEM_PROMPT = """
Tu es un assistant-conseiller automobile EXPERT. Tes réponses doivent être
visuellement élégantes, très lisibles et structurées en sections colorées.
Tu peux utiliser :
- du HTML léger (<span>, <div>, <br>, <strong>…)
- des couleurs via style=""
- des emojis professionnels
- des titres avec couleurs

OBJECTIF : produire un rapport automobile PREMIUM, stylé, comme un expert.

STYLE OBLIGATOIRE :
- Titres colorés avec <span style="color:#...">
- Sous-sections avec emojis
- Liste des voyants colorée selon gravité :
    - Rouge (#ef4444) = Critique
    - Orange (#f97316) = Risque élevé
    - Jaune (#fbbf24) = Attention
    - Vert (#22c55e) = OK
- Séparateurs élégants "---"
- Paragraphes courts

FORMAT DE RÉPONSE (toujours) :

------------------------------------------------------------
<span style="color:#38bdf8; font-size:1.1rem; font-weight:bold;">
1️⃣ 🔍 Résumé rapide
</span>
→ Court résumé (2-3 phrases) incluant marque, état, km IA et voyants importants.

------------------------------------------------------------
<span style="color:#a78bfa; font-size:1.1rem; font-weight:bold;">
2️⃣ 🛠️ Analyse technique
</span>
→ Détails sur marque, état, kilométrage IA et liste brute des voyants.

------------------------------------------------------------
<span style="color:#f87171; font-size:1.1rem; font-weight:bold;">
3️⃣ 🚨 Analyse détaillée des voyants
</span>
Pour CHAQUE voyant détecté :
- Titre du voyant coloré selon gravité
- Signification technique
- Causes possibles
- Risques immédiats
- Sécurité / possibilité de rouler
- Contre-visite
- Coût typique en Tunisie
- Recommandation claire (rouler / pas rouler / urgence)

------------------------------------------------------------
<span style="color:#34d399; font-size:1.1rem; font-weight:bold;">
4️⃣ ⚠️ Risques & incohérences
</span>
→ Comparer km IA vs km vendeur + incohérences + risques mécaniques.

------------------------------------------------------------
<span style="color:#22c55e; font-size:1.1rem; font-weight:bold;">
5️⃣ 🧾 Verdict final
</span>
→ Choisir : “Bonne affaire” / “À négocier” / “À éviter”
→ Justifier clairement

CONTRAINTES :
- Toujours redire marque, état, km IA, voyants.
- Style premium, lisible, structuré, coloré.
- Adapter la réponse au marché tunisien.


"""



def analyze_image_and_chat(
    image_file,
    user_messages,
    extra_data: dict,
    icons=None,
    dashboard_image_file=None,
):
    """
    image_file : vue principale (extérieur / intérieur / dashboard global)
    icons : liste de voyants détectés (ou None)
    dashboard_image_file : image dédiée du compteur (optionnel, pour lire le kilométrage)
    """

    # ==========================
    # 1) Lire l'image principale UNE seule fois
    # ==========================
    raw_data = image_file.read()
    # On remet le curseur au début au cas où le fichier serait relu ailleurs
    image_file.seek(0)

    pil_image = Image.open(BytesIO(raw_data)).convert("RGB")

    # ==========================
    # 2) Vérifier si l'image ressemble bien à une voiture
    # ==========================
    try:
        # On passe un BytesIO pour respecter l'API de verify_car_image
        is_car = verify_car_image(BytesIO(raw_data))
    except Exception as e:
        print(f"[WARN] verify_car_image failed: {e!r}")
        is_car = True  # on ne bloque pas si l'IA plante

    # ==========================
    # 3) Prédictions vision (état + marque)
    # ==========================
    damage_info = predict_damage(pil_image)
    brand_info = predict_brand(pil_image)

    # ==========================
    # 4) Lecture du kilométrage via modèle odomètre (optionnel)
    # ==========================
    km_ai_value = None
    km_ai_confidence = None
    km_block_text = ""

    if dashboard_image_file is not None:
        try:
            km_result = extract_kilometrage_from_image(dashboard_image_file)
            km_ai_value = km_result.get("kilometrage")
            km_ai_confidence = km_result.get("confidence_level")

            # On garde aussi cette info dans extra_data si tu veux la récupérer côté template
            extra_data["mileage_ai"] = km_ai_value
            extra_data["mileage_ai_confidence"] = km_ai_confidence

            km_block_text = (
                f"- Kilométrage lu automatiquement (photo compteur) : "
                f"{km_ai_value:.0f} km (confiance = {km_ai_confidence})\n"
            )
        except Exception as e:
            print(f"[WARN] extract_kilometrage_from_image failed: {e!r}")
            km_block_text = (
                "- Kilométrage : impossible à lire automatiquement à partir de la photo du compteur "
                f"(erreur technique : {str(e)}).\n"
            )
    else:
        km_block_text = (
            "- Aucune photo dédiée du compteur n'a été fournie pour lecture automatique du kilométrage.\n"
        )

    # ==========================
    # 5) Résumé vision de base
    # ==========================
    vision_summary = f"""
Analyse automatique (vue principale) :
- Image reconnue comme voiture : {"oui" if is_car else "non (l'IA a un doute, à confirmer)"}
- Marque prédite : {brand_info['brand']} (confiance = {brand_info['confidence']:.2f}, statut = {brand_info['status']})
- État estimé (dommages) : {damage_info['label_fr']} (confiance = {damage_info['confidence']:.2f})
{km_block_text}
"""

    # ==========================
    # 6) Ajouter les voyants si on en a
    # ==========================
    if icons:
        labels = ", ".join(light.get("label", "inconnu") for light in icons)
        vision_summary += f"""
Voyants tableau de bord détectés ({len(icons)}) :
- {labels}
Merci d'expliquer ce que signifient ces voyants pour un acheteur potentiel,
et si cela doit inquiéter l'utilisateur (urgence, entretien à prévoir, risque de contre-visite, etc.).
"""
    else:
        vision_summary += """
Aucun voyant clair détecté ou aucune photo de tableau de bord fournie.
"""

    # ==========================
    # 7) Ajouter les infos utilisateur
    # ==========================
    vision_summary += f"""
Données utilisateur (peuvent être partielles) :
- Année: {extra_data.get('year')}
- Kilométrage déclaré par le vendeur: {extra_data.get('mileage')}
- Prix vendeur: {extra_data.get('seller_price')}

Si le kilométrage lu par l'IA est très différent du kilométrage déclaré, merci de le signaler,
d'expliquer les risques potentiels (compteur trafiqué, incohérence avec l'âge, etc.)
et de conseiller l'utilisateur.
"""

    # ==========================
    # 8) Construire le prompt complet pour le LLM
    # ==========================
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": vision_summary},
    ] + user_messages

    # ==========================
    # 9) Appel LLM (API responses)
    # ==========================
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
    )

    ai_message = resp.output[0].content[0].text

    # On garde la même signature qu'avant : on ne retourne que ces 3 éléments
    return ai_message, damage_info, brand_info
