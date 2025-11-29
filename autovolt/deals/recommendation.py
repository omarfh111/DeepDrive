# deals/recommendation.py
import csv
import json
import os
from decimal import Decimal

from django.conf import settings

from .models import *
from .emails import send_recommendation_email

from openai import OpenAI

# ⚙️ Client OpenAI (clé dans settings.OPENAI_API_KEY)

client = OpenAI(
    api_key=getattr(settings, "OPENAI_API_KEY", None)
)

# ⚙️ Emplacement du CSV (à adapter à ton projet)

VEHICLES_CSV_PATH = os.path.join(
    settings.BASE_DIR,
    "data",
    "vehicles.csv",
)



# ========= 1. Appel LLM : analyse du partenaire =========

import json
from json import JSONDecodeError

import json
from json import JSONDecodeError

def analyze_partner_with_llm(partenariat):
    budget = int(partenariat.plafond_effectif)

    system_message = (
        "Tu es un assistant spécialisé en analyse de besoins de mobilité pour des entreprises. "
        "À partir du nom d'une société, de la description de ses activités et d'un budget total, "
        "tu dois déduire le secteur principal, les usages probables des véhicules et des contraintes "
        "de recommandation de véhicules. "
        "Tu DOIS toujours répondre uniquement en JSON strictement valide, sans texte autour."
    )

    user_message = f"""
Analyse les informations suivantes sur une entreprise et produis un JSON structuré
selon le schéma ci-dessous.

Données d'entrée :
- Nom de la société : {partenariat.nom_societe}
- Description : {partenariat.detail_societe}
- Budget total (plafond) : {budget} dinars

Objectif :
1. Déterminer le secteur principal de l'entreprise (parmi : "educatif","logistique","sante",
   "btp","vtc","livraison","agricole","industrie","administration","autre").
2. Décrire l'usage principal des véhicules.
3. Proposer des contraintes de recommandation adaptées au budget et à l'activité.

Schéma JSON attendu :

{{
  "company_name": "string",
  "raw_description": "string",
  "budget_total": nombre_entier,

  "sector": "string",
  "sector_confidence": nombre_reel_entre_0_et_1,

  "main_use_case": "string",
  "usage_tags": ["string", "string"],

  "constraints": {{
    "max_price_per_vehicle": nombre_entier_ou_null,
    "min_number_of_vehicles": nombre_entier_ou_null,
    "prefered_brands": ["string"],
    "avoid_brands": ["string"],
    "priority": ["string"],
    "notes": "string"
  }},

  "recommendation_strategy": {{
    "type": "string",
    "comment": "string"
  }}
}}

Règles :
- "sector" doit être choisi dans la liste donnée.
- "sector_confidence" doit être un nombre entre 0 et 1.
- "usage_tags" doit contenir entre 2 et 5 étiquettes maximum.
- Réponds uniquement avec le JSON, sans texte avant ni après.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        max_tokens=800,
    )

    text = resp.choices[0].message.content or ""

    # 🔧 1) enlever les ```...``` éventuels
    text = text.strip()
    if text.startswith("```"):
        # on garde tout ce qui est entre le premier { et le dernier }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

    # 🔧 2) remplacer les sauts de ligne bruts par des espaces (sinon JSON invalide)
    text = text.replace("\r", " ").replace("\n", " ")

    try:
        data = json.loads(text)
    except JSONDecodeError:
        print("=== TEXTE RECU PAR LE LLM (toujours non JSON valide) ===")
        print(text)
        # 🔁 Fallback simple : valeur par défaut pour ne pas tout casser
        data = {
            "company_name": partenariat.nom_societe or "",
            "raw_description": partenariat.detail_societe or "",
            "budget_total": budget,
            "sector": "autre",
            "sector_confidence": 0.0,
            "main_use_case": "",
            "usage_tags": [],
            "constraints": {
                "max_price_per_vehicle": None,
                "min_number_of_vehicles": None,
                "prefered_brands": [],
                "avoid_brands": [],
                "priority": [],
                "notes": "",
            },
            "recommendation_strategy": {
                "type": "fallback",
                "comment": "LLM JSON parsing failed, using default analysis."
            }
        }

    return data



# ========= 2. Chargement du CSV véhicules =========
def load_vehicles_from_csv(debug=False):
    """
    Charge le CSV des véhicules.

    CSV actuel (d'après ton debug) :
    - Première colonne : '\ufeffmodele' (ex: 'Bako Bee', 'NouveauAvantier Avantier C', ...)
    - prix : nombre brut
    - prix_texte : texte avec 'DT', etc.
    - url_modele
    - brand : contient en fait 'electrique' (motorisation) => pas fiable pour la marque

    Logique :
    - On lit le champ '\ufeffmodele' ou 'modele'
    - On en déduit :
        brand  = premier mot significatif (en enlevant 'Nouveau', 'Nouvelle', 'New')
        modele = reste de la chaîne
    - On nettoie le prix
    - On filtre les prix absurdes (> 500000 TND)
    - On dé-duplique par url_modele
    """
    vehicles = []

    if not os.path.exists(VEHICLES_CSV_PATH):
        if debug:
            print("⚠️ CSV introuvable :", VEHICLES_CSV_PATH)
        return vehicles

    seen_urls = set()

    with open(VEHICLES_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if debug:
            print("Colonnes CSV vues :", reader.fieldnames)

        for i, row in enumerate(reader, start=1):
            if debug and i <= 5:
                print(f"Row {i} brut :", row)

            # 1) Récupération du "modele" réel (colonne avec BOM ou normale)
            raw_full_model = (row.get("\ufeffmodele") or row.get("modele") or "").strip()
            if not raw_full_model:
                if debug:
                    print(f"⚠️ Ligne {i} ignorée : modele vide")
                continue

            # 2) Déduction de la marque et du modèle
            #    Exemple: "Bako Bee" -> brand="Bako", modele="Bee"
            #             "NouveauAvantier Avantier C" -> enlever "NouveauAvantier" ? on simplifie :
            tokens = raw_full_model.split()
            # On enlève certains préfixes marketing
            while tokens and tokens[0].lower().startswith(("nouveau", "nouvelle", "new")):
                tokens = tokens[1:]

            if not tokens:
                if debug:
                    print(f"⚠️ Ligne {i} ignorée : tokens vides après nettoyage")
                continue

            brand = tokens[0]
            modele = " ".join(tokens[1:]) if len(tokens) > 1 else brand

            url_modele = (row.get("url_modele") or "").strip()
            if not url_modele:
                if debug:
                    print(f"⚠️ Ligne {i} ignorée : url_modele vide")
                continue

            # 3) Nettoyage du prix
            raw_prix = str(row.get("prix", "")).strip()
            raw_prix = raw_prix.replace(" ", "").replace(",", ".")
            try:
                prix = Decimal(raw_prix)
            except Exception:
                if debug:
                    print(f"⚠️ Prix invalide à la ligne {i} :", raw_prix)
                continue

            # On élimine les prix "monstrueux" (cas 225868900 => bug de scraping)
            if prix > Decimal("500000"):
                if debug:
                    print(f"⚠️ Prix aberrant à la ligne {i} ({prix}), ligne ignorée")
                continue

            # 4) Déduplication par URL
            if url_modele in seen_urls:
                continue
            seen_urls.add(url_modele)

            vehicles.append(
                {
                    "modele": modele,
                    "brand": brand,
                    "prix": prix,
                    "prix_texte": (row.get("prix_texte") or "").strip(),
                    "url_modele": url_modele,
                }
            )

    if debug:
        print(f"✅ {len(vehicles)} véhicules chargés après nettoyage.")
        # Affiche les 5 premiers pour vérif
        for v in vehicles[:5]:
            print("→", v)

    return vehicles




# ========= 3. Logique de filtrage / scoring =========

def score_vehicle(v, analysis: dict, budget_total: Decimal, max_price_per_vehicle: Decimal) -> float:
    """
    Donne un score à un véhicule en fonction :
    - du prix par rapport au budget / max_price_per_vehicle
    - du secteur
    - des marques préférées / à éviter
    """
    sector = (analysis.get("sector") or "").lower()
    constraints = analysis.get("constraints") or {}
    prefered_brands = [b.lower() for b in (constraints.get("prefered_brands") or [])]
    avoid_brands = [b.lower() for b in (constraints.get("avoid_brands") or [])]

    brand = (v["brand"] or "").lower()
    modele = (v["modele"] or "").lower()
    prix = v["prix"]

    score = 0.0

    # 1) Adéquation prix vs max_price_per_vehicle (idéal ~ 60-80% du max)
    if max_price_per_vehicle and max_price_per_vehicle > 0:
        ratio = float(prix / max_price_per_vehicle)  # 0.0 = très cheap, 1.0 = au plafond
        ideal = 0.7
        score += max(0.0, 1.0 - abs(ratio - ideal)) * 5.0  # max +5 pts

    # 2) Bonus si le véhicule ne consomme pas tout le budget
    if budget_total and budget_total > 0:
        global_ratio = float(prix / budget_total)  # part du budget que prend ce véhicule
        if global_ratio <= 0.5:
            score += 1.0  # ne consomme pas trop le budget
        elif global_ratio >= 0.9:
            score -= 1.0  # trop cher par rapport au budget global

    # 3) Marques préférées / à éviter
    if prefered_brands and brand in prefered_brands:
        score += 3.0
    if avoid_brands and brand in avoid_brands:
        score -= 5.0

    # 4) Heuristiques par secteur
    if sector == "educatif":
        # on aime les véhicules pas trop chers pour transport d'élèves
        if prix <= Decimal("60000"):
            score += 2.0
        if any(x in modele for x in ["van", "combi", "bus", "commuter"]):
            score += 1.5

    elif sector in ["logistique", "livraison", "btp"]:
        # plutôt utilitaires : van, pickup, box, etc.
        if any(x in modele for x in ["van", "box", "pickup", "truck", "logistar"]):
            score += 2.5

    elif sector == "vtc":
        # VTC : on aime les berlines/confort
        if any(x in modele for x in ["class", "series", "passat", "octavia", "civic", "camry"]):
            score += 2.5

    # 5) Petit bonus pour modèles identifiés (pas vide)
    if modele:
        score += 0.5

    return score



def build_recommendations(partenariat, analysis: dict, max_results: int = 8) -> dict:
    budget_total = partenariat.plafond_effectif
    constraints = analysis.get("constraints") or {}

    max_price_per_vehicle = constraints.get("max_price_per_vehicle")
    try:
        if max_price_per_vehicle:
            max_price_per_vehicle = Decimal(str(max_price_per_vehicle))
        else:
            max_price_per_vehicle = budget_total
    except Exception:
        max_price_per_vehicle = budget_total

    all_vehicles = load_vehicles_from_csv()

    candidates = [
        v for v in all_vehicles
        if v["prix"] > 0 and v["prix"] <= max_price_per_vehicle
    ]

    scored = []
    for v in candidates:
        s = score_vehicle(v, analysis, budget_total, max_price_per_vehicle)  # ✅ ici
        scored.append({**v, "score": s})

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected = []
    total_cost = Decimal("0.00")
    for v in scored:
        if len(selected) >= max_results:
            break
        if total_cost + v["prix"] > budget_total:
            continue
        selected.append(v)
        total_cost += v["prix"]

    return {
        "partner_id": partenariat.id_partenariat,
        "budget_total": str(budget_total),
        "currency": "TND",
        "analysis": analysis,
        "recommended_vehicles": [
            {
                "modele": v["modele"],
                "brand": v["brand"],
                "prix": str(v["prix"]),
                "prix_texte": v["prix_texte"],
                "url_modele": v["url_modele"],
                "score": round(v["score"], 3),
            }
            for v in selected
        ],
        "total_estimated_cost": str(total_cost),
        "count": len(selected),
    }


# ========= 4. Pipeline complet (appelé depuis le signal) =========

def run_recommendation_pipeline(partenariat):
    """
    Pipeline complet :
    - analyse LLM
    - filtrage CSV
    - envoi de l'email de recommandation
    """
    if not partenariat.plafond_effectif or partenariat.plafond_effectif <= 0:
        # Pas de plafond => on ne recommande rien
        return

    analysis = analyze_partner_with_llm(partenariat)
    result = build_recommendations(partenariat, analysis)

    # Envoi d'un email au partenaire
    send_recommendation_email(partenariat, result)

    # Option : tu peux aussi loguer ou stocker ce JSON en base si tu veux.
    return result