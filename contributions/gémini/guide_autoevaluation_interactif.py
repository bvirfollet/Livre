"""
Guide d'Autoévaluation Interactif & Questionnaire IA
====================================================
Projet RadioHumaine / Géométrie de la Cognition
Auteur : Bertrand Virfollet & Gemini (Août 2026)

Ce script guide pas-à-pas l'utilisateur pour évaluer ses paramètres émotionnels
et cognitifs (K_ana, S_eff, K_mém, Phase de Berry, Valence, Arousal, Résonance)
grâce à un générateur adaptatif de questions contextualisées par IA.

Utilisation :
  python3 contributions/gémini/guide_autoevaluation_interactif.py
  python3 contributions/gémini/guide_autoevaluation_interactif.py --demo
"""

import sys
import os
import json
import time
import datetime
import numpy as np

# ═══════════════════════════════════════════════════════════════
# 1. Moteur de Génération Adaptative de Questions par IA
# ═══════════════════════════════════════════════════════════════

class AIQuestionGenerator:
    """
    Génère dynamiquement des questions d'autoévaluation contextualisées
    selon le domaine d'expérience (Couple, Pro, Décision Individuelle).
    """
    CONTEXTS = {
        "1": "Relationnel / Couple",
        "2": "Professionnel / Architecture & Ingénierie",
        "3": "Décision Personnelle / Existentielle"
    }

    QUESTIONS_DATABASE = {
        "K_ana": [
            {
                "id": "kana_1",
                "dimension": "Pression Analytique (K_ana)",
                "prompts": {
                    "1": "Face à une tension dans le couple, à quel point ressentez-vous le besoin de trancher immédiatement en isolant chaque mot (1 = lâcher-prise/flou accepté, 10 = besoin de clarification chirurgicale) ?",
                    "2": "Face à un blocage technique ou un conflit d'architecture, à quel point exigez-vous une procédure stricte sans concession (1 = souplesse/exploration, 10 = contrôle total/norme stricte) ?",
                    "3": "Face à une décision personnelle, à quel point votre esprit boucle-t-il sur les critères d'optimisation (1 = intuition/mouvement, 10 = sur-analyse/paralysie) ?"
                }
            },
            {
                "id": "kana_2",
                "dimension": "Pression Analytique (K_ana)",
                "prompts": {
                    "1": "Quel est votre niveau d'impatience ou de fatigue face aux approximations de votre partenaire (1 = très tolérant, 10 = exaspération immédiate) ?",
                    "2": "Quel est votre niveau de pression temporelle perçu pour imposer la bonne solution (1 = temps long, 10 = urgence critique) ?",
                    "3": "À quel point ressentez-vous une tension musculaire ou cognitive pendant votre réflexion (1 = détente/flow, 10 = forte crispation) ?"
                }
            }
        ],
        "S_eff": [
            {
                "id": "seff_1",
                "dimension": "Nuance Perçue & Complexité (S_eff)",
                "prompts": {
                    "1": "Parvenez-vous à percevoir la part de vérité de votre partenaire en même temps que la vôtre (1 = vision binaire opposée, 10 = intégration simultanée des deux nuances) ?",
                    "2": "Dans l'analyse du problème, distinguez-vous de multiples alternatives viables (1 = solution unique ou rien, 10 = éventail riche de trajectoires) ?",
                    "3": "Voyez-vous la situation sous des angles contradictoires mais légitimes (1 = noir ou blanc, 10 = haute densité de nuance) ?"
                }
            }
        ],
        "K_mem": [
            {
                "id": "kmem_1",
                "dimension": "Charge Mémorielle & Veto (K_mém)",
                "prompts": {
                    "1": "À quel point un événement passé ou une ancienne dispute influence-t-il votre réaction actuelle (1 = aucun poids du passé, 10 = présence d'un 'vieux dossier' bloquant) ?",
                    "2": "À quel point un passif d'erreurs ou de compromis dégradés pèse-t-il dans l'échange (1 = repart de zéro, 10 = veto mémoriel actif) ?",
                    "3": "Ressentez-vous qu'une expérience passée limite ce qu'il vous est possible d'envisager aujourd'hui (1 = espace vierge, 10 = contrainte mémorielle forte) ?"
                }
            },
            {
                "id": "kmem_2",
                "dimension": "Amnistie Topologique (Purge du Veto)",
                "prompts": {
                    "1": "Êtes-vous disposé(e) à appliquer une amnistie topologique : effacer le grief tout en conservant la leçon apprise (1 = impossible d'oublier la charge, 10 = amnistie totale avec résidu K_inf) ?",
                    "2": "Pouvez-vous réinitialiser le dialogue sans récriminations si la leçon technique est tirée (1 = rancœur tenace, 10 = amnistie immédiate) ?",
                    "3": "Êtes-vous prêt(e) à tourner la page en gardant la sagesse acquise (1 = verrouillé sur le grief, 10 = amnistie fluide) ?"
                }
            }
        ],
        "Berry": [
            {
                "id": "berry_1",
                "dimension": "Holonomie Relationnelle & Phase de Berry (γ_Berry)",
                "prompts": {
                    "1": "Après avoir traversé ce cycle d'échange, revenez-vous au sujet initial avec une posture transformée (1 = retour au point de départ identique, 10 = déphasage fructueux / vision renouvelée) ?",
                    "2": "Le parcours de discussion a-t-il laissé une empreinte géométrique durable dans votre rapport au projet (1 = aucun changement, 10 = transformation nette de la relation) ?",
                    "3": "Ressentez-vous que la boucle de réflexion a enrichi la compréhension du problème (1 = boucle stérile, 10 = holonomie positive) ?"
                }
            }
        ],
        "Emotional": [
            {
                "id": "emo_valence",
                "dimension": "Valence Émotionnelle",
                "prompts": {
                    "1": "Quelle est la tonalité affective globale de l'échange (1 = très désagréable/hostile, 10 = très harmonieux/lumineux) ?",
                    "2": "Comment qualifiez-vous l'atmosphère de travail (1 = tendue/toxique, 10 = stimulante/bienveillante) ?",
                    "3": "Quel est votre état émotionnel interne (1 = anxiété/abattement, 10 = clarté/sérénité) ?"
                }
            },
            {
                "id": "emo_arousal",
                "dimension": "Niveau d'Activation / Excitation (Arousal)",
                "prompts": {
                    "1": "Quel est votre niveau d'excitation/agitation interne (1 = calme/léthargie, 10 = surexcitation/hyper-réactivité) ?",
                    "2": "Quel est l'impact sur votre énergie (1 = épuisement/vide, 10 = surtension) ?",
                    "3": "À quel rythme battent vos pensées (1 = ralenti, 10 = bouillonnement rapide) ?"
                }
            }
        ]
    }

    def __init__(self, context_key="1"):
        self.context_key = context_key if context_key in self.CONTEXTS else "1"
        self.context_name = self.CONTEXTS[self.context_key]

    def get_questions(self):
        """Retourne la liste des questions adaptées au contexte sélectionné."""
        questions_list = []
        for category, items in self.QUESTIONS_DATABASE.items():
            for q_data in items:
                prompt_text = q_data["prompts"].get(self.context_key, q_data["prompts"]["1"])
                questions_list.append({
                    "id": q_data["id"],
                    "dimension": q_data["dimension"],
                    "prompt": prompt_text
                })
        return questions_list


# ═══════════════════════════════════════════════════════════════
# 2. Calculateur d'Estimateurs & Diagnostiqueur du Garant
# ═══════════════════════════════════════════════════════════════

class EvaluatorEngine:
    """
    Calcule les estimateurs formels (K_ana, S_eff, K_mém, Berry, Valence, Arousal)
    et génère le diagnostic avec la posture recommandée du Garant.
    """
    @staticmethod
    def process_responses(responses):
        # Extraction des scores (1-10)
        k1 = responses.get("kana_1", 5.0)
        k2 = responses.get("kana_2", 5.0)
        s1 = responses.get("seff_1", 5.0)
        m1 = responses.get("kmem_1", 5.0)
        m2 = responses.get("kmem_2", 5.0)
        b1 = responses.get("berry_1", 5.0)
        v1 = responses.get("emo_valence", 5.0)
        a1 = responses.get("emo_arousal", 5.0)

        # Normalisation [0.0, 1.0]
        K_ana = float((k1 + k2) / 2.0 - 1.0) / 9.0
        S_eff = float(s1 - 1.0) / 9.0
        K_veto = float(m1 - 1.0) / 9.0
        Amnesty_readiness = float(m2 - 1.0) / 9.0
        Berry_phase = float(b1 - 1.0) / 9.0 * np.pi  # en radians [0, pi]
        Valence = float(v1 - 1.0) / 9.0
        Arousal = float(a1 - 1.0) / 9.0

        # Détermination de la Posture Recommandée du Garant
        K_c = 0.5  # Point d'inflexion idéal
        delta_K = K_ana - K_c

        if K_ana > 0.75:
            posture = "L'Accordeur de Phase (Détente de K_ana)"
            conseil = ("Votre pression analytique K_ana est très élevée (> 0.75). Vous êtes en sur-contrôle ou rigidité. "
                       "Recommandation : Réduire K_ana par 15 min de silence partagé, musique instrumentale, "
                       "ou acceptation délibérée d'une zone de flou.")
        elif K_ana < 0.25:
            posture = "La Forge Sémantique (Rigidification constructive)"
            conseil = ("Votre pression analytique K_ana est faible (< 0.25). Risque de manque de structure ou d'évitement. "
                       "Recommandation : Augmenter K_ana en isolant précisément le point nodal du désaccord "
                       "et en reformulant les définitions jusqu'à validation stricte.")
        else:
            posture = "La Posture Propre du Garant (Zone d'Inflexion K_c ≈ 0.5)"
            conseil = ("Vous êtes dans la zone d'inflexion optimale (K_ana ≈ 0.5). "
                       "C'est la posture propre du Garant : habiter la tension sans la fuir ni imposer un dogme. "
                       "Votre réactivité spectrale est maximale.")

        if K_veto > 0.6 and Amnesty_readiness > 0.5:
            conseil += "\n▶ Opportunité d'Amnistie Topologique : Le veto mémoriel est lourd mais votre disposition est favorable. Effacez la charge K0 tout en conservant la leçon résiduelle K_inf."

        return {
            "K_ana": round(K_ana, 4),
            "S_eff": round(S_eff, 4),
            "K_veto": round(K_veto, 4),
            "Amnesty_readiness": round(Amnesty_readiness, 4),
            "Berry_phase_rad": round(Berry_phase, 4),
            "Valence": round(Valence, 4),
            "Arousal": round(Arousal, 4),
            "Posture_Garant": posture,
            "Recommandation": conseil
        }


# ═══════════════════════════════════════════════════════════════
# 3. Interface CLI Interactive & Mode Démo
# ═══════════════════════════════════════════════════════════════

def run_interactive_guide(demo_mode=False):
    print("=" * 68)
    print("  GUIDE D'AUTOÉVALUATION INTERACTIF & QUESTIONNAIRE IA")
    print("  Projet RadioHumaine / Géométrie de la Cognition")
    print("=" * 68)
    print()

    if demo_mode:
        print("[MODE DÉMO AUTOMATISÉ ENCLENCHÉ]")
        context_key = "1"
        responses = {
            "kana_1": 8.0,
            "kana_2": 7.0,
            "seff_1": 6.0,
            "kmem_1": 7.0,
            "kmem_2": 8.0,
            "berry_1": 7.5,
            "emo_valence": 6.5,
            "emo_arousal": 7.0
        }
    else:
        print("Veuillez choisir le contexte de votre évaluation :")
        print("  1. Relationnel / Couple")
        print("  2. Professionnel / Architecture & Ingénierie")
        print("  3. Décision Personnelle / Existentielle")
        context_key = input("Votre choix (1-3) [défaut: 1] : ").strip() or "1"
        if context_key not in ["1", "2", "3"]:
            context_key = "1"
            
        generator = AIQuestionGenerator(context_key)
        questions = generator.get_questions()
        
        print(f"\n---> Contexte retenu : {generator.context_name}")
        print("---> Répondez à chaque question sur une échelle de 1 (Faible) à 10 (Élevé).\n")
        
        responses = {}
        for q in questions:
            print(f"[{q['dimension']}]")
            print(f"  {q['prompt']}")
            val_str = input("  Note (1-10) [défaut: 5] : ").strip() or "5"
            try:
                val = float(val_str)
                val = max(1.0, min(10.0, val))
            except ValueError:
                val = 5.0
            responses[q["id"]] = val
            print()

    # Traitement des résultats
    results = EvaluatorEngine.process_responses(responses)
    context_name = AIQuestionGenerator.CONTEXTS.get(context_key, "Inconnu")

    print("\n" + "=" * 68)
    print("                    RAPPORT DE DIAGNOSTIC")
    print("=" * 68)
    print(f" Contexte : {context_name}")
    print(f" Date     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 68)
    print(f" ► Pression Analytique (K_ana)  : {results['K_ana']:.4f}  (1-10 équiv: {1 + 9*results['K_ana']:.1f})")
    print(f" ► Nuance Perçue (S_eff)       : {results['S_eff']:.4f}  (1-10 équiv: {1 + 9*results['S_eff']:.1f})")
    print(f" ► Charge de Veto (K_mém)       : {results['K_veto']:.4f}")
    print(f" ► Disposition Amnistie        : {results['Amnesty_readiness']:.4f}")
    print(f" ► Phase de Berry (γ_Berry)     : {results['Berry_phase_rad']:.4f} rad")
    print(f" ► Valence Émotionnelle         : {results['Valence']:.4f}")
    print(f" ► Activation (Arousal)         : {results['Arousal']:.4f}")
    print("-" * 68)
    print(f" POSTURE RECOMMANDÉE DU GARANT : {results['Posture_Garant']}")
    print(f"\n RECOMMANDATION :\n {results['Recommandation']}")
    print("=" * 68)

    # Sauvegarde du rapport JSON
    output_dir = "/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"session_autoevaluation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)

    export_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context_name,
        "raw_responses": responses,
        "computed_estimators": results
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"\nRapport de session exporté avec succès -> {filepath}\n")
    return export_data


if __name__ == "__main__":
    demo = "--demo" in sys.argv
    run_interactive_guide(demo_mode=demo)
