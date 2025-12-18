"""
Estimation intelligente des coûts avec Groq (ULTRA RAPIDE & GRATUIT)
"""
import os
import json
from groq import Groq

class CostEstimator:
    """Estime les coûts de réparation avec Groq"""
    
    def __init__(self, api_key=None):
        """
        Initialise l'estimateur
        
        Args:
            api_key: Clé API Groq (optionnel, sinon env var)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY manquante. "
                "Obtenez-la gratuitement sur https://console.groq.com"
            )
        
        self.client = Groq(api_key=self.api_key)
        
        # Modèle à utiliser (choix recommandés)
        # "llama3-70b-8192" → Plus intelligent, 30 req/min
        # "mixtral-8x7b-32768" → Plus rapide, 30 req/min
        # "gemma-7b-it" → Très rapide, léger
        self.model = "llama3-70b-8192"  # RECOMMANDÉ
    
    def estimate(self, damages, vehicle_info=None):
        """
        Estime les coûts de réparation avec Groq
        
        Args:
            damages: Liste des dommages détectés par YOLOv8
            vehicle_info: Infos sur le véhicule (optionnel)
            
        Returns:
            dict: Estimation détaillée
        """
        # Construire le prompt
        prompt = self._build_prompt(damages, vehicle_info)
        
        print(f"🚀 Consultation de Groq ({self.model})...")
        
        try:
            # Appeler Groq (ULTRA RAPIDE !)
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en estimation de coûts de réparation automobile en Tunisie. Tu réponds UNIQUEMENT en JSON valide, sans markdown."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,  # Peu de créativité, plus factuel
                max_tokens=1000,
                top_p=1,
                stream=False
            )
            
            # Extraire la réponse
            response_text = chat_completion.choices[0].message.content
            
            # Nettoyer le JSON (enlever markdown si présent)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parser la réponse JSON
            estimation = json.loads(response_text)
            print(f"✅ Estimation reçue en {chat_completion.usage.total_time:.2f}s : {estimation['total_range']}")
            
            return estimation
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur parsing JSON : {e}")
            print(f"Réponse brute : {response_text[:200]}")
            return self._fallback_estimation(damages)
        except Exception as e:
            print(f"❌ Erreur Groq : {e}")
            return self._fallback_estimation(damages)
    
    def _build_prompt(self, damages, vehicle_info):
        """Construit le prompt pour Groq"""
        
        # Informations sur les dommages
        damages_desc = []
        for i, damage in enumerate(damages, 1):
            bbox = damage['bbox']
            size = (bbox['x2'] - bbox['x1']) * (bbox['y2'] - bbox['y1'])
            damages_desc.append(
                f"{i}. **{damage['type']}** "
                f"(confiance: {damage['confidence']:.1f}%, "
                f"taille: {size}px², "
                f"position: x={bbox['x1']}-{bbox['x2']}, y={bbox['y1']}-{bbox['y2']})"
            )
        
        damages_text = "\n".join(damages_desc)
        
        # Infos véhicule (si disponibles)
        vehicle_text = ""
        if vehicle_info:
            vehicle_text = f"\n\n**Véhicule :** {vehicle_info}"
        
        # Prompt structuré
        prompt = f"""Tu es un expert en estimation de coûts de réparation automobile en Tunisie.

Voici les dommages détectés par une IA sur un véhicule :{vehicle_text}

{damages_text}

**Analyse ces dommages et fournis une estimation des coûts de réparation en dinars tunisiens (DT).**

**Prends en compte :**
- La gravité de chaque dommage (basée sur la taille, la position, et la confiance de détection)
- Les interactions entre dommages (plusieurs dommages proches peuvent nécessiter plus de travail)
- Les coûts typiques en Tunisie pour ce type de réparation
- La position du dommage (capot, porte, pare-choc = coûts différents)

**IMPORTANT : Réponds UNIQUEMENT avec un objet JSON valide (sans markdown, sans backticks) dans ce format exact :**

{{
  "details": [
    {{
      "type": "Bosse",
      "cost_min": 200,
      "cost_max": 350,
      "justification": "Bosse importante nécessitant débosselage professionnel et retouche peinture"
    }}
  ],
  "total_min": 200,
  "total_max": 350,
  "total_range": "200-350 DT",
  "analysis": "Analyse globale des dommages et de leur impact sur le coût total",
  "recommendations": [
    "Conseil 1",
    "Conseil 2"
  ]
}}

Réponds maintenant avec le JSON uniquement :"""
        
        return prompt
    
    def _fallback_estimation(self, damages):
        """Estimation de secours si Groq échoue"""
        print("⚠️ Utilisation estimation basique (fallback)")
        
        cost_ranges = {
            'Bosse': (150, 400),
            'Rayure': (100, 300),
            'Fissure': (200, 600),
            'Verre brisé': (300, 800),
            'Lampe cassée': (150, 500),
            'Pneu crevé': (80, 200)
        }
        
        total_min = 0
        total_max = 0
        details = []
        
        for damage in damages:
            damage_type = damage['type']
            min_cost, max_cost = cost_ranges.get(damage_type, (100, 500))
            
            # Ajuster selon la confiance
            confidence_factor = damage['confidence'] / 100
            min_cost = int(min_cost * confidence_factor)
            max_cost = int(max_cost * confidence_factor)
            
            # Ajuster selon la taille
            bbox = damage['bbox']
            size = (bbox['x2'] - bbox['x1']) * (bbox['y2'] - bbox['y1'])
            if size > 50000:  # Grand dommage
                min_cost = int(min_cost * 1.3)
                max_cost = int(max_cost * 1.3)
            
            total_min += min_cost
            total_max += max_cost
            
            details.append({
                'type': damage_type,
                'cost_min': min_cost,
                'cost_max': max_cost,
                'justification': f"Estimation automatique (confiance: {damage['confidence']:.1f}%)"
            })
        
        return {
            'details': details,
            'total_min': total_min,
            'total_max': total_max,
            'total_range': f"{total_min}-{total_max} DT",
            'analysis': "Estimation automatique basique. Groq n'a pas pu générer une estimation détaillée.",
            'recommendations': [
                "Consulter 2-3 carrossiers pour des devis précis",
                "Prendre des photos détaillées de chaque dommage"
            ]
        }