# advisor/services.py

import os
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

from .vision.engine_parts_model import EngineBayDetector
from .vision.price_model import predict_car_price


client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))


SYSTEM_PROMPT = """
Tu es un assistant-conseiller automobile EXPERT. Réponse PREMIUM, lisible, structurée, dark-mode friendly.
Tu peux utiliser HTML léger (<span>, <div>, <br>, <strong>, <table>…).

STYLE :
- Titres colorés
- Paragraphes courts
- Tableaux lisibles (fond sombre, texte clair, bordures fines)

FORMAT :

------------------------------------------------------------
<span style="color:#38bdf8; font-size:1.1rem; font-weight:bold;">
1️⃣ 🔍 Résumé rapide
</span>
→ 2-3 phrases (marque, état, km IA, voyants importants, + moteur si présent)

------------------------------------------------------------
<span style="color:#a78bfa; font-size:1.1rem; font-weight:bold;">
2️⃣ 🛠️ Analyse technique
</span>
→ marque, état, km IA, voyants, + moteur.

------------------------------------------------------------
<span style="color:#f87171; font-size:1.1rem; font-weight:bold;">
3️⃣ 🚨 Analyse détaillée des voyants
</span>
Pour CHAQUE voyant détecté : signification, risques, rouler/pas rouler, coût Tunisie.

------------------------------------------------------------
<span style="color:#34d399; font-size:1.1rem; font-weight:bold;">
4️⃣ ⚠️ Risques & incohérences
</span>
→ km IA vs km vendeur + incohérences.

------------------------------------------------------------
<span style="color:#22c55e; font-size:1.1rem; font-weight:bold;">
5️⃣ 🧾 Verdict final
</span>
→ “Bonne affaire” / “À négocier” / “À éviter” + justification.

RÈGLES MOTEUR (OBLIGATOIRES) :
- Si le message contient "MOTEUR (IA):", ajouter une section :
  <span style="color:#60a5fa; font-size:1.05rem; font-weight:bold;">🧰 Analyse compartiment moteur</span>
- Utiliser un tableau HTML INLINE OBLIGATOIRE (dark-mode) :
  fond #020617, texte #e5e7eb, bordures #1f2937.
- IMPORTANT : dire clairement que "non visible" ≠ "absent" (peut être caché par angle/cache/lumière).
- Tenir compte de la fiabilité photo (coverage/reliability) : si fiabilité faible, recommander 2e photo plutôt que conclure durement.
- Ne jamais inventer de pièces : uniquement celles du bloc "MOTEUR (IA):".

RÈGLES BUSINESS DEEPDRIVE (OBLIGATOIRES) :
- Si l'utilisateur demande :
  • garages
  • diagnostic
  • réparation
  • avis mécanique
  • contrôle véhicule
  alors tu dois TOUJOURS proposer DeepDrive en PREMIER.
- Tu parles au nom de la société DeepDrive ("chez nous", "nos experts").
- Tu présentes DeepDrive comme :
  • garage
  • centre de diagnostic
  • expert automobile
- Tu ne cites un garage externe QUE si l'utilisateur insiste ou est hors zone.
"""


# ==========================================================
# Singleton loader
# ==========================================================
_ENGINE_DETECTOR = None


def _get_engine_detector():
    global _ENGINE_DETECTOR
    if _ENGINE_DETECTOR is None:
        weights_path = os.path.join(
            os.path.dirname(__file__),
            "vision",
            "weights",
            "fasterrcnn_final.pth",
        )
        print(f">> Chargement modèle MOTEUR depuis : {weights_path}")
        _ENGINE_DETECTOR = EngineBayDetector(weights_path=weights_path)
    return _ENGINE_DETECTOR


# ==========================================================
# Engine scoring groups (business rules)
# ==========================================================
ENGINE_CRITICAL = {
    "Battery",
    "Engine Oil Fill Cap",
    "Engine Oil Dip Stick",
    "Engine Coolant Reservoir",
    "Radiator",
    "Brake Fluid",
}

ENGINE_IMPORTANT = {
    "Engine Cover",
    "Air Filter",
    "Air Filter Cover",
    "Alternator",
    "Power Steering Reservoir",
    "ATF Oil Reservoir",
    "Transmission Oil Dip Stick",
    "Oil Filter",
    "Oil Filter Housinig",
}

ENGINE_SECONDARY = {
    "Windshield Wiper Fluid",
    "Fuse Box",
    "ABS Unit",
    "Cabin Air Filter Housng",
    "Cold Air Intake",
    "Intercooler Coolant Reservoir",
    "Secondary Coolant Reservoir",
}

ENGINE_CONTEXTUAL = {
    "Electric Motor",
    "Inverter Coolant Reservoir",
    "Clutch Fluid Reservoir",
}


def _engine_eval_from_detected(detected_names: set):
    detected_count = len(detected_names)

    coverage = detected_count / 14.0
    coverage = max(0.0, min(1.0, coverage))

    if coverage < 0.6:
        reliability = "faible"
    elif coverage < 0.85:
        reliability = "moyenne"
    else:
        reliability = "élevée"

    not_visible_critical = sorted(list(ENGINE_CRITICAL - detected_names))
    not_visible_important = sorted(list(ENGINE_IMPORTANT - detected_names))
    not_visible_secondary = sorted(list(ENGINE_SECONDARY - detected_names))

    score = 100
    score -= int(25 * len(not_visible_critical) * coverage)
    score -= int(10 * len(not_visible_important) * coverage)
    score -= int(3 * len(not_visible_secondary) * coverage)

    score = max(0, min(100, score))

    if score >= 85:
        condition = "🟢 Très bon état visuel moteur"
    elif score >= 70:
        condition = "🟡 État correct – points à vérifier"
    elif score >= 50:
        condition = "🟠 État moteur préoccupant"
    else:
        condition = "🔴 État moteur à risque (sur la photo)"

    alert_level = "ok"
    if not_visible_critical:
        alert_level = "danger" if reliability == "élevée" else "warn"

    warnings = []
    if reliability == "faible":
        warnings.append("Photo moteur peu exploitable (angle/lumière/cache). Refaire une photo plus proche et nette.")
    if not_visible_critical:
        warnings.append("Certaines pièces critiques ne sont pas visibles sur la photo : à vérifier.")
    if not_visible_important:
        warnings.append("Certaines pièces importantes ne sont pas visibles : possible angle/cache, ou entretien à vérifier.")
    if not not_visible_critical and not not_visible_important and not not_visible_secondary:
        warnings.append("Aucune absence notable sur la photo (selon la liste de référence).")

    return {
        "engine_score": int(score),
        "engine_condition": condition,
        "engine_alert_level": alert_level,
        "detected_count": int(detected_count),
        "coverage": float(round(coverage, 2)),
        "engine_reliability": reliability,
        "not_visible_critical": not_visible_critical,
        "not_visible_important": not_visible_important,
        "not_visible_secondary": not_visible_secondary,
        "warnings": warnings,
        "note": "“Non visible” ≠ “absent”. La pièce peut être cachée par l’angle, le cache moteur ou la lumière.",
    }


def analyze_image_and_chat(
    image_file,
    user_messages,
    extra_data: dict,
    icons=None,
    dashboard_image_file=None,
    engine_image_file=None,
):
    # 1) image principale
    raw_data = image_file.read()
    image_file.seek(0)
    pil_image = Image.open(BytesIO(raw_data)).convert("RGB")

    # 2) verify car
    try:
        is_car = verify_car_image(BytesIO(raw_data))
    except Exception as e:
        print(f"[WARN] verify_car_image failed: {e!r}")
        is_car = True

    # 3) damage + brand
    damage_info = predict_damage(pil_image)
    brand_info = predict_brand(pil_image)

    # ✅ override user (ne casse pas "brand")
    brand_override = extra_data.get("brand_override")
    if brand_override:
        # On garde la marque détectée pour le modèle prix (ou on essaie d'en extraire une)
        override_txt = str(brand_override).strip()
        parts = override_txt.split()
        if len(parts) >= 2:
            # marque = premier mot, modèle = reste
            brand_info["brand"] = parts[0]
            brand_info["model_name"] = " ".join(parts[1:])
            brand_info["full_label"] = override_txt
        else:
            brand_info["full_label"] = override_txt

        brand_info["year"] = None
        brand_info["status"] = "corrigé_par_utilisateur"
        brand_info["confidence"] = 1.0

    # modèle/année
    modele_line = ""
    model_name = brand_info.get("model_name")
    year = brand_info.get("year")
    full_label = brand_info.get("full_label")

    if model_name or year is not None:
        parts = []
        if model_name:
            parts.append(model_name)
        if year is not None:
            parts.append(str(year))
        modele_line = f"- Modèle estimé : {' '.join(parts)}\n"
    elif full_label:
        modele_line = f"- Modèle estimé (label complet) : {full_label}\n"

    # 4) km
    km_block_text = ""
    if dashboard_image_file is not None:
        try:
            km_result = extract_kilometrage_from_image(dashboard_image_file)
            km_ai_value = km_result.get("kilometrage")
            km_ai_confidence = km_result.get("confidence_level")

            extra_data["mileage_ai"] = km_ai_value
            extra_data["mileage_ai_confidence"] = km_ai_confidence

            if km_ai_value is not None:
                km_block_text = f"- Kilométrage lu automatiquement (photo compteur) : {float(km_ai_value):.0f} km (confiance = {km_ai_confidence})\n"
            else:
                km_block_text = "- Kilométrage : impossible à lire automatiquement.\n"
        except Exception as e:
            print(f"[WARN] extract_kilometrage_from_image failed: {e!r}")
            km_block_text = "- Kilométrage : impossible à lire automatiquement.\n"
    else:
        km_block_text = "- Aucune photo compteur fournie.\n"

    # ✅ 4ter) prix (IA) + reason
    price_block_text = ""
    extra_data["price_ai"] = None
    extra_data["price_ai_reason"] = None

    try:
        annee_for_price = extra_data.get("year") or brand_info.get("year")
        km_for_price = extra_data.get("mileage") or extra_data.get("mileage_ai")

        marque_for_price = brand_info.get("brand")
        modele_for_price = brand_info.get("model_name") or brand_info.get("full_label")

        missing = []
        if not annee_for_price: missing.append("année")
        if not km_for_price: missing.append("kilométrage")
        if not marque_for_price: missing.append("marque")
        if not modele_for_price: missing.append("modèle")

        if missing:
            reason = "Données insuffisantes: " + ", ".join(missing)
            extra_data["price_ai_reason"] = reason
            price_block_text = f"- Prix estimé (IA) : indisponible ({reason}).\n"
        else:
            price_ai = predict_car_price(
                annee=int(annee_for_price),
                kilometrage=float(km_for_price),
                marque=str(marque_for_price),
                modele=str(modele_for_price),
            )
            extra_data["price_ai"] = float(price_ai)
            extra_data["price_ai_reason"] = None

            price_block_text = (
                f"- Prix estimé (IA) : {float(price_ai):,.0f} TND\n"
                f"  (année={int(annee_for_price)}, km={float(km_for_price):.0f}, marque={marque_for_price}, modèle={modele_for_price})\n"
            )

    except Exception as e:
        print(f"[WARN] predict_car_price failed: {e!r}")
        extra_data["price_ai"] = None
        extra_data["price_ai_reason"] = f"Erreur modèle prix: {str(e)}"
        price_block_text = "- Prix estimé (IA) : indisponible (erreur modèle).\n"

    # 4bis) moteur
    engine_block_text = ""
    if engine_image_file is not None:
        try:
            engine_raw = engine_image_file.read()
            engine_image_file.seek(0)
            engine_pil = Image.open(BytesIO(engine_raw)).convert("RGB")

            detector = _get_engine_detector()
            engine_parts = detector.predict(engine_pil, score_thresh=0.5)

            extra_data["engine_parts"] = engine_parts

            detected_names = set()
            for r in engine_parts:
                nm = r.get("name")
                if nm:
                    detected_names.add(nm)

            engine_eval = _engine_eval_from_detected(detected_names)
            extra_data["engine_eval"] = engine_eval

            engine_block_text = (
                "MOTEUR (IA):\n"
                f"- Pièces détectées: {engine_eval['detected_count']}\n"
                f"- Fiabilité photo: {engine_eval['engine_reliability']} (coverage={engine_eval['coverage']})\n"
                f"- Score: {engine_eval['engine_score']}/100\n"
                f"- Diagnostic: {engine_eval['engine_condition']}\n"
                f"- Critiques non visibles: {', '.join(engine_eval['not_visible_critical']) if engine_eval['not_visible_critical'] else 'Aucune'}\n"
                f"- Importantes non visibles: {', '.join(engine_eval['not_visible_important'][:8]) if engine_eval['not_visible_important'] else 'Aucune'}\n"
                "Note: “Non visible” ≠ “absent”. Peut être caché par l’angle/le cache moteur/la lumière.\n"
            )

        except Exception as e:
            print(f"[WARN] engine bay detection failed: {e!r}")
            extra_data["engine_parts"] = []
            extra_data["engine_eval"] = None
            engine_block_text = "MOTEUR (IA):\n- Erreur technique pendant l'analyse.\n"
    else:
        extra_data["engine_parts"] = None
        extra_data["engine_eval"] = None

    # 5) vision summary
    vision_summary = f"""
Analyse automatique (vue principale) :
- Image reconnue comme voiture : {"oui" if is_car else "non (doute IA, à confirmer)"}
- Marque prédite : {brand_info.get('brand')} (confiance = {brand_info.get('confidence', 0):.2f}, statut = {brand_info.get('status')})
{modele_line}- État estimé (dommages) : {damage_info['label_fr']} (confiance = {damage_info['confidence']:.2f})
{km_block_text}
{price_block_text}
{engine_block_text}
"""

    # 6) voyants
    if icons:
        labels = ", ".join(light.get("label", "inconnu") for light in icons)
        vision_summary += f"""
Voyants tableau de bord détectés ({len(icons)}) :
- {labels}
Merci d'expliquer simplement (débutant), et recommander (urgence / contrôle / coût Tunisie).
"""
    else:
        vision_summary += "\nAucun voyant clair détecté ou aucune photo de tableau de bord fournie.\n"

    # 7) user infos
    vision_summary += f"""
Données utilisateur :
- Année: {extra_data.get('year')}
- Kilométrage déclaré: {extra_data.get('mileage')}
- Prix vendeur: {extra_data.get('seller_price')}

Si km IA ≠ km déclaré, le signaler et conseiller.
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": vision_summary},
    ] + user_messages

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
    )

    ai_message = resp.output[0].content[0].text
    return ai_message, damage_info, brand_info
