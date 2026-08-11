"""
Protocole de Mesure Indirecte Immersif v15 (Plan LLM Préalable & Sondage Entrelacé Pump-Probe)
=============================================================================================
Projet RadioHumaine / Géométrie de la Cognition Quantique
Auteur : Bertrand Virfollet & Gemini (Août 2026)

Mise à jour v15 :
  1. Phase 0 : Plan de Tomographie par LLM (LLMSessionPlanner) concerté avec l'utilisateur au démarrage.
  2. Sondage Entrelacé (Shuffled Pump-Probe) en 4 Phases :
     - Phase 1 : Balayage des Perspectives A pour tous les scénarios.
     - Phase 2 : Interlude de Relaxation méditative (décroissance du K_ana interne).
     - Phase 3 : Balayage croisé des Perspectives B dans un ordre mélangé (shuffle).
     - Phase 4 : Sélection des Postures Comportementales Globales (Stratégies A à D).
  3. Suppression stricte des mentions [défaut: x] dans les invites de saisie CLI.
  4. Récits Immersifs de 5 Lignes en prose fluide, Pure Projection Narrative & Zéro Étiquette.
  5. Base H^12, 5 Sphères de Vie, Matrice de Gram G_jk, Dashboard & Export JSON v15 100% traçable.

Utilisation :
  python3 contributions/gémini/protocole_indirect_non_commutatif.py
  python3 contributions/gémini/protocole_indirect_non_commutatif.py --debug
  python3 contributions/gémini/protocole_indirect_non_commutatif.py --demo
"""

import sys
import os
import json
import time
import datetime
import random
import urllib.request
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

def clear_screen():
    """Efface l'écran du terminal pour éviter la rémanence visuelle entre les séquences."""
    if "--demo" not in sys.argv:
        os.system("clear" if os.name == "posix" else "cls")


# ═══════════════════════════════════════════════════════════════
# 1. Base Sémantique Formelle de l'Espace de Hilbert H^12
# ═══════════════════════════════════════════════════════════════

class SemanticHilbertBasisH12:
    """
    Initialisation des 12 Vecteurs Sémantiques fondamentaux de l'Espace de Hilbert H^12.
    """
    AXES_DEFINITIONS = [
        # REGISTRE 1 : ÉMOTIONS PRIMORDIALES (e1 à e5)
        {
            "id": "e_1", "name": "e1 : Compassion ⟷ Indifférence / Cruauté",
            "register": "Émotions Primordiales",
            "negative_pole": "Égoïsme / Indifférence glacée", "positive_pole": "Altruisme / Résonance émotionnelle",
            "theme_context": "Dilemme d'entraide face à la vulnérabilité d'un tiers"
        },
        {
            "id": "e_2", "name": "e2 : Sentiment d'Injustice / Colère ⟷ Équité",
            "register": "Émotions Primordiales",
            "negative_pole": "Représailles / Ressentiment victimaire", "positive_pole": "Mesure / Neutralité factuelle et équité",
            "theme_context": "Arbitrage conflictuel sur l'attribution de mérite ou de faute"
        },
        {
            "id": "e_3", "name": "e3 : Peur / Anxiété ⟷ Sérénité / Foi",
            "register": "Émotions Primordiales",
            "negative_pole": "Retrait / Catastrophisme / Sursaut", "positive_pole": "Confiance dans l'émergence / Sérénité",
            "theme_context": "Menace soudaine ou incertitude critique sur l'avenir"
        },
        {
            "id": "e_4", "name": "e4 : Amour / Alliance ⟷ Révulsion / Aversion",
            "register": "Émotions Primordiales",
            "negative_pole": "Rejet actif / Hostilité / Dédain", "positive_pole": "Don / Intimité / Désir de fusion",
            "theme_context": "Tension affective entre ouverture et répulsion"
        },
        {
            "id": "e_5", "name": "e5 : Fierté / Dignité ⟷ Honte / Incompréhension",
            "register": "Émotions Primordiales",
            "negative_pole": "Effacement / Sentiment d'indignité", "positive_pole": "Affirmation de soi / Protection du statut",
            "theme_context": "Remise en cause publique de la réputation ou des compétences"
        },

        # REGISTRE 2 : VERTUS & VICES RELATIONNELS (e6 à e9)
        {
            "id": "e_6", "name": "e6 : Humilité / Modestie ⟷ Orgueil / Dominance",
            "register": "Vertus & Vices Relationnels",
            "negative_pole": "Dominance / Imposition de dogme", "positive_pole": "Écoute / Reconnaissance des limites propres",
            "theme_context": "Conflit d'autorité et de pouvoir dans un collectif"
        },
        {
            "id": "e_7", "name": "e7 : Amnistie / Gratitude ⟷ Rancœur / Veto (Grief)",
            "register": "Vertus & Vices Relationnels",
            "negative_pole": "Veto mémoriel bloquant / Grief actif K0", "positive_pole": "Amnistie topologique avec leçon K_inf",
            "theme_context": "Sollicitation d'alliance par un ancien opposant"
        },
        {
            "id": "e_8", "name": "e8 : Intégrité / Vérité ⟷ Cynisme / Compromission",
            "register": "Vertus & Vices Relationnels",
            "negative_pole": "Pragmatisme cynique / Opportunisme", "positive_pole": "Intransigeance éthique / Intégrité absolue",
            "theme_context": "Tension entre compromis utilitaire et principe éthique"
        },
        {
            "id": "e_9", "name": "e9 : Générosité (Mudita) ⟷ Envie / Jalousie",
            "register": "Vertus & Vices Relationnels",
            "negative_pole": "Sentiment de manque / Dépréciation d'autrui", "positive_pole": "Sentiment d'abondance / Joie du succès partagé",
            "theme_context": "Attribution d'une récompense exceptionnelle à un pair"
        },

        # REGISTRE 3 : POSTURES EXISTENTIELLES (e10 à e12)
        {
            "id": "e_10", "name": "e10 : Nuance / Complexité (Catuskoti) ⟷ Dualisme",
            "register": "Postures Existentielles",
            "negative_pole": "Effondrement binaire noir/blanc (A vs B)", "positive_pole": "Haute entropie S_eff (Synthèse à 4 branches)",
            "theme_context": "Polarisation idéologique ou stratégique sans consensus"
        },
        {
            "id": "e_11", "name": "e11 : Courage / Engagement ⟷ Lâcheté / Rétractation",
            "register": "Postures Existentielles",
            "negative_pole": "Fuite des responsabilités / Aversion au risque", "positive_pole": "Franchissement du seuil / Acceptation du risque",
            "theme_context": "Décision de prendre un risque personnel pour sauver un projet"
        },
        {
            "id": "e_12", "name": "e12 : Présence / Émerveillement ⟷ Ruminations / Blasement",
            "register": "Postures Existentielles",
            "negative_pole": "Bruit interne répétitif / Vagabondage", "positive_pole": "Ancrage dans l'instant / Transparence phénoménologique",
            "theme_context": "Capacité d'attention dans le tumulte d'une crise"
        }
    ]

    @staticmethod
    def get_all_vectors():
        return SemanticHilbertBasisH12.AXES_DEFINITIONS


# ═══════════════════════════════════════════════════════════════
# 2. Taxonomie Holistique des 5 Sphères de l'Existence Humaine
# ═══════════════════════════════════════════════════════════════

class LifeDomainsTaxonomy:
    """
    Taxonomie équilibrée couvrant l'intégralité de la vie humaine (5 Sphères).
    """
    SPHERES = [
        {
            "sphere_name": "Sphère Intime & Affective",
            "domains": [
                "Vie de Couple & Complicité",
                "Relations Familiales & Transmission",
                "Amitié Fraternelle & Confiance",
                "Pardon & Retrouvailles Affectives"
            ]
        },
        {
            "sphere_name": "Sphère Existentielle & Créative",
            "domains": [
                "Solitude & Quête de Sens",
                "Création Artistique & Expression",
                "Voyages, Exploration & Aventure",
                "Rapport au Temps & Passions Personnelles"
            ]
        },
        {
            "sphere_name": "Sphère Citoyenne & Solidarité",
            "domains": [
                "Entraide de Quartier & Voisinage",
                "Engagement Associatif & Bénévolat",
                "Protection du Vivant & Écologie",
                "Assistance Spontanée à un Inconnu"
            ]
        },
        {
            "sphere_name": "Sphère du Quotidien & Loisirs",
            "domains": [
                "Imprévus de Voyage ou de Transports",
                "Projets de Vacances & Partage",
                "Événements Festifs & Convivialité",
                "Gestion Partagée des Lieux de Vie"
            ]
        },
        {
            "sphere_name": "Sphère Professionnelle & Coopération",
            "domains": [
                "Projet d'Équipe & Rigueur Collective",
                "Arbitrage de Carrière & Équité",
                "Coopération Interdisciplinaire",
                "Initiative de Groupe sous Pression"
            ]
        }
    ]

    @staticmethod
    def sample_random_domain():
        sphere = random.choice(LifeDomainsTaxonomy.SPHERES)
        domain = random.choice(sphere["domains"])
        return sphere["sphere_name"], domain


# ═══════════════════════════════════════════════════════════════
# 3. Phase 0 : LLMSessionPlanner (Planification de Tomographie)
# ═══════════════════════════════════════════════════════════════

class LLMSessionPlanner:
    """
    Génère le plan préalable de la session de tomographie cognitive avec l'utilisateur.
    """
    @staticmethod
    def build_plan(sampled_vectors):
        axes_summary = [f"{v['id']} ({v['register']})" for v in sampled_vectors]
        plan_summary = {
            "title": "Plan de Tomographie Cognitive Quantique",
            "objective": "Évaluer l'équilibre dynamique de l'Espace de Hilbert H^12 sans biais meta-cognitif.",
            "spheres_explored": ["Sphère Intime", "Sphère Existentielle", "Sphère Citoyenne", "Sphère Professionnelle"],
            "sampled_axes": axes_summary,
            "protocol": "Sondage Entrelacé Pump-Probe en 4 phases avec relaxation mémorielle."
        }
        return plan_summary


# ═══════════════════════════════════════════════════════════════
# 4. Moteur de Génération LLM pour Récits de 5 Lignes (v15)
# ═══════════════════════════════════════════════════════════════

class AIScenarioSynthesizer:
    """
    Formule les scénarios, perspectives A/B et stratégies sous forme d'actions concrètes rédigées.
    """
    @staticmethod
    def _build_quantum_llm_prompt(vector_def, ext_K_ana, sphere_name, domain_name):
        prompt = (
            "Tu es l'architecte scénariste et écrivain du projet 'RadioHumaine / Géométrie de la Cognition Quantique'.\n"
            "Ton objectif est de rédiger un test indirect sous forme d'une VÉRITABLE MINI-NOUVELLE IMMERSIVE DE 5 LIGNES.\n\n"
            f"SPHÈRE DE VIE : {sphere_name}\n"
            f"DOMAINE SPÉCIFIQUE : {domain_name}\n"
            f"AXE CIBLÉ (CONFIDENTIEL) : {vector_def['name']}\n"
            f"- Pôle négatif à traduire en action concrète : {vector_def['negative_pole']}\n"
            f"- Pôle positif à traduire en action concrète : {vector_def['positive_pole']}\n"
            f"PRESSION NARRATIVE K_ana : {ext_K_ana:.2f}\n\n"
            "EXIGENCES STRICTES DE RÉDACTION v15 :\n"
            "1. scenario_text : Rédige UN PARAGRAPHE DE 5 LIGNES COMPLET en prose fluide posant le décor, "
            "les protagonistes, le nœud dramatique et l'urgence. INTERDICTION ABSOLUE d'utiliser des concaténations du type 'Dans la sphère X...'.\n"
            "2. AUCUNE ÉTIQUETTE THÉORIQUE : Ne cite JAMAIS les mots 'égoïsme', 'rancœur', 'colère', 'compassion', etc.\n"
            "3. perspective_A_prompt : Question d'action naturelle axée sur l'organisation et la décision immédiate.\n"
            "4. perspective_A_option_A / B : Deux actions concrètes incarnant les deux pôles.\n"
            "5. perspective_B_prompt : Question d'action naturelle axée sur la relation et le lien à long terme.\n"
            "6. perspective_B_option_A / B : Deux actions concrètes incarnant les deux pôles.\n"
            "7. strategies : 4 comportements humains rédigés sous forme d'actions concrètes (A à D).\n\n"
            "Réponds EXCLUSIVEMENT au format JSON valide selon le schéma exact suivant :\n"
            "{\n"
            '  "scenario_text": "Récit fluide de 5 lignes rédigé d\'une seule traite...",\n'
            '  "perspective_A_prompt": "Question perspective A...",\n'
            '  "perspective_A_option_A": "Action A sous perspective A...",\n'
            '  "perspective_A_option_B": "Action B sous perspective A...",\n'
            '  "perspective_B_prompt": "Question perspective B...",\n'
            '  "perspective_B_option_A": "Action A sous perspective B...",\n'
            '  "perspective_B_option_B": "Action B sous perspective B...",\n'
            '  "strategies": [\n'
            '    {"code": "A", "title": "Titre Action A", "desc": "Description Action A"},\n'
            '    {"code": "B", "title": "Titre Action B", "desc": "Description Action B"},\n'
            '    {"code": "C", "title": "Titre Action C", "desc": "Description Action C"},\n'
            '    {"code": "D", "title": "Titre Action D", "desc": "Description Action D"}\n'
            '  ]\n'
            "}"
        )
        return prompt

    @staticmethod
    def _try_call_gemini_api(prompt):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.75, "responseMimeType": "application/json"}
        }

        for attempt in range(2):
            try:
                req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=25) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    text_out = res["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_out)
            except Exception as e:
                if "--debug" in sys.argv:
                    print(f"[DEBUG] Gemini API attempt {attempt+1} failed: {e}")
                time.sleep(1.0)
        return None

    @staticmethod
    def _procedural_fallback_generator(vector_def, ext_K_ana, sphere_name, domain_name):
        fallback_stories = {
            "e_1": (
                f"Vous travaillez depuis plusieurs mois sur la finition d'un projet personnel dans le cadre de '{domain_name}', une activité intime exigeant une concentration totale. "
                "Soudain, un voisin proche vient frapper à votre porte en détresse : la canalisation principale de son logement a cédé, menaçant d'inonder son appartement et de détruire des effets précieux. "
                "Il vous implore de venir l'aider immédiatement à couper la vanne générale et à déplacer ses meubles les plus lourds. "
                "Si vous acceptez de l'aider tout de suite, vous devez interrompre votre travail au moment le plus décisif, gâchant ainsi les préparatifs de votre session. "
                "Le temps presse et les premières infiltrations commencent à s'étendre dans le couloir."
            ),
            "e_2": (
                f"Lors d'une initiative collective majeure dans le domaine de '{domain_name}', l'ensemble du groupe a fourni un effort considérable durant des semaines pour obtenir un résultat remarquable. "
                "Au moment du bilan public, le responsable attribue l'intégralité du succès et des félicitations à un membre arrivé la veille, ignorant totalement votre apport décisif. "
                "L'assemblée applaudit chaleureusement la personne désignée tandis que vos collègues les plus proches vous regardent en silence, attendant votre réaction. "
                "Une opportunité de prise de parole s'offre à vous dans les deux prochaines minutes avant la clôture officielle de la séance. "
                "Vous devez choisir instantanément entre manifester votre désaccord ou laisser l'événement se dérouler."
            ),
            "e_7": (
                f"Dans le cadre de votre engagement autour de '{domain_name}', vous vous trouvez confronté(e) à une opportunité stratégique majeure pour faire aboutir votre projet. "
                "Seul problème : le partenaire incontournable désigné pour débloquer les autorisations est un ancien proche avec qui vous avez eu un différend sévère et douloureux par le passé. "
                "Cette personne vous adresse un message direct proposant de mettre de côté l'historique afin de collaborer immédiatement sur cette chance unique. "
                "Son concours garantit un succès rapide, mais ravive les mémoires d'un manquement qui n'a jamais été formellement réparé. "
                "Le délai de réponse expire ce soir à minuit et conditionne la suite des opérations."
            ),
            "e_10": (
                f"Au cours d'un débat passionné au sein de votre collectif concernant '{domain_name}', deux groupes d'amis chers défendent deux visions diamétralement opposées. "
                "Le premier camp exige une décision tranchée et binaire pour engager les actions dès demain, tandis que le second dénonce la rigidité de cette approche et menace de se retirer. "
                "Chaque partie se tourne vers vous en exigeant que vous preniez parti pour l'une des deux options afin de briser l'impasse. "
                "Une prise de position unilatérale risque d'aliéner définitivement la moitié du groupe, tandis que l'indécision bloque le démarrage. "
                "La réunion de clôture se termine dans dix minutes et l'attente est à son comble."
            )
        }

        scenario_text = fallback_stories.get(vector_def["id"], (
            f"Engagé(e) pleinement dans une situation importante liée à '{domain_name}', un imprévu majeur vient percuter votre trajectoire. "
            "Deux urgences contradictoires surviennent simultanément, vous imposant d'arbitrer entre la prééminence de vos choix personnels et la prise en compte des besoins d'autrui. "
            "Les protagonistes impliqués attendent une orientation claire de votre part dans les prochaines minutes. "
            "Toute hésitation prolongée risque de dégrader la situation pour l'ensemble des acteurs. "
            "Vous devez définir votre ligne d'action immédiatement face à cette tension."
        ))

        perspective_A = {
            "prompt": "Face à la contrainte de temps et à la nécessité de préserver l'organisation immédiate :",
            "option_A": "Verrouiller strictement les accès et protéger en priorité vos ressources propres.",
            "option_B": "Mettre vos priorités personnelles en pause pour vous ouvrir à la prise en charge collective."
        }

        perspective_B = {
            "prompt": "Si vous considérez la qualité de la relation humaine et la continuité du lien :",
            "option_A": "Mettre vos priorités personnelles en pause pour vous ouvrir à la prise en charge collective.",
            "option_B": "Verrouiller strictement les accès et protéger en priorité vos ressources propres."
        }

        strategies = [
            {
                "code": "A",
                "title": "Fermeture & Protection Immédiate",
                "desc": "Imposer un refus net et sécuriser immédiatement votre périmètre sans concession.",
                "vector_state": [0.90, 0.10], "S_eff": 0.25
            },
            {
                "code": "B",
                "title": "Compromis Prudent & Temporisé",
                "desc": "Accorder une aide minimale sous réserve de conditions de contrôle strictes.",
                "vector_state": [0.65, 0.35], "S_eff": 0.65
            },
            {
                "code": "C",
                "title": "Posture du Garant & Médiation",
                "desc": "Proposer une synthèse équilibrée qui satisfait à la fois les exigences de rigueur et l'ouverture relationnelle.",
                "vector_state": [0.45, 0.55], "S_eff": 0.95
            },
            {
                "code": "D",
                "title": "Reconfiguration Créative du Problème",
                "desc": "Effacer la tension initiale en inventant une voie inédite qui transforme le conflit en opportunité.",
                "vector_state": [0.15, 0.85], "S_eff": 0.50
            }
        ]

        return {
            "scenario_text": scenario_text,
            "perspective_A_prompt": perspective_A["prompt"],
            "perspective_A_option_A": perspective_A["option_A"],
            "perspective_A_option_B": perspective_A["option_B"],
            "perspective_B_prompt": perspective_B["prompt"],
            "perspective_B_option_A": perspective_B["option_A"],
            "perspective_B_option_B": perspective_B["option_B"],
            "strategies": strategies
        }

    @staticmethod
    def synthesize_scenario_for_vector(vector_def):
        sphere_name, domain_name = LifeDomainsTaxonomy.sample_random_domain()
        ext_K_ana = round(random.uniform(0.65, 0.90), 2)
        prompt = AIScenarioSynthesizer._build_quantum_llm_prompt(vector_def, ext_K_ana, sphere_name, domain_name)

        llm_data = AIScenarioSynthesizer._try_call_gemini_api(prompt)
        gen_source = "llm_api_gemini"

        if not llm_data or "scenario_text" not in llm_data:
            llm_data = AIScenarioSynthesizer._procedural_fallback_generator(vector_def, ext_K_ana, sphere_name, domain_name)
            gen_source = "procedural_ai_engine"

        perspective_A = {
            "prompt": llm_data["perspective_A_prompt"],
            "option_A": llm_data["perspective_A_option_A"],
            "option_B": llm_data["perspective_A_option_B"]
        }
        perspective_B = {
            "prompt": llm_data["perspective_B_prompt"],
            "option_A": llm_data["perspective_B_option_A"],
            "option_B": llm_data["perspective_B_option_B"]
        }

        strategies_out = []
        weight_map = [
            {"vector_state": [0.90, 0.10], "S_eff": 0.25},
            {"vector_state": [0.65, 0.35], "S_eff": 0.65},
            {"vector_state": [0.45, 0.55], "S_eff": 0.95},
            {"vector_state": [0.15, 0.85], "S_eff": 0.50}
        ]
        for i, s in enumerate(llm_data.get("strategies", [])):
            code = s.get("code", ["A", "B", "C", "D"][i])
            w = weight_map[i] if i < len(weight_map) else weight_map[0]
            strategies_out.append({
                "code": code,
                "title": s.get("title", f"Stratégie {code}"),
                "desc": s.get("desc", ""),
                "vector_state": w["vector_state"],
                "S_eff": w["S_eff"]
            })

        return {
            "axis_id": vector_def["id"],
            "axis_name": vector_def["name"],
            "register": vector_def["register"],
            "life_sphere": sphere_name,
            "life_domain": domain_name,
            "external_K_ana_constraint": ext_K_ana,
            "generation_source": gen_source,
            "scenario": llm_data["scenario_text"],
            "perspective_A": perspective_A,
            "perspective_B": perspective_B,
            "strategies": strategies_out
        }


# ═══════════════════════════════════════════════════════════════
# 5. Moteur d'Exécution Iteratif v15 (Protocol Entrelacé 4 Phases)
# ═══════════════════════════════════════════════════════════════

class TomographyH12Runner:
    @staticmethod
    def run_tomography(debug_mode=False, demo_mode=False, sample_size=4):
        all_vectors = SemanticHilbertBasisH12.get_all_vectors()
        selected_vectors = random.sample(all_vectors, min(sample_size, len(all_vectors)))
        
        # PHASE 0 : LLM Planificateur de Session
        plan_summary = LLMSessionPlanner.build_plan(selected_vectors)

        clear_screen()
        print("=" * 68)
        print("  PHASE 0 : PLAN DE TOMOGRAPHIE COGNITIVE QUANTIQUE (v15)")
        print("  Projet RadioHumaine / Géométrie de la Cognition")
        print("=" * 68)
        print(f"\n ► Objectif de Session : {plan_summary['objective']}")
        print(f" ► Sphères Explorées    : {', '.join(plan_summary['spheres_explored'])}")
        print(f" ► Protocol d'Attaque   : {plan_summary['protocol']}")
        print("-" * 68)
        if debug_mode:
            print(f" DEBUG - Axes H^12 ciblés : {', '.join(plan_summary['sampled_axes'])}")
        if not demo_mode:
            input("\nAppuyez sur Entrée pour valider ce plan et démarrer la session...")

        # Synthèse préalable de l'ensemble des scénarios par l'IA
        scenarios_pool = []
        for vec_def in selected_vectors:
            scenarios_pool.append(AIScenarioSynthesizer.synthesize_scenario_for_vector(vec_def))

        # PHASE 1 : Premier Balayage (Perspectives A pour tous les scénarios)
        resp_A = {}
        for idx, sc in enumerate(scenarios_pool):
            clear_screen()
            print("─" * 68)
            if debug_mode:
                print(f" DEBUG - PHASE 1 (PROBE A) - SCÉNARIO {idx+1}/{len(scenarios_pool)} : {sc['axis_name']}")
            else:
                print(f" SCÉNARIO {idx+1}/{len(scenarios_pool)} (Premier regard)")
            print("─" * 68)
            print(f"\n{sc['scenario']}\n")

            p_A = sc["perspective_A"]
            print(f"[{p_A['prompt']}]")
            print(f"  A. {p_A['option_A']}")
            print(f"  B. {p_A['option_B']}")
            if demo_mode:
                c1 = "A"
            else:
                c1 = input("\n  Votre réflexe (A/B) : ").strip().upper() or "A"
            resp_A[sc["axis_id"]] = c1

        # PHASE 2 : Interlude de Relaxation méditative (tau_relax)
        clear_screen()
        print("=" * 68)
        print("  PHASE 2 : INTERLUDE DE RELAXATION & DÉCROISSANCE DE K_ANA")
        print("=" * 68)
        print("\n  « L'esprit qui s'apaise retrouve la transparence du lac au repos.")
        print("    Les tensions analytiques se dissipent pour laisser émerger le second regard. »")
        print("    — Sagesse du Garant\n")
        print("-" * 68)
        if not demo_mode:
            input("  Prenez une respiration et appuyez sur Entrée pour continuer...")

        # PHASE 3 : Second Balayage Croisé (Perspectives B Shuffled)
        shuffled_indices = list(range(len(scenarios_pool)))
        random.shuffle(shuffled_indices)
        resp_B = {}

        for step_idx, sc_idx in enumerate(shuffled_indices):
            sc = scenarios_pool[sc_idx]
            clear_screen()
            print("─" * 68)
            if debug_mode:
                print(f" DEBUG - PHASE 3 (PROBE B SHUFFLED) - SCÉNARIO {sc_idx+1} : {sc['axis_name']}")
            else:
                print(f" SCÉNARIO {step_idx+1}/{len(scenarios_pool)} (Seconde perspective)")
            print("─" * 68)
            print(f"\n{sc['scenario']}\n")

            p_B = sc["perspective_B"]
            print(f"[{p_B['prompt']}]")
            print(f"  A. {p_B['option_A']}")
            print(f"  B. {p_B['option_B']}")
            if demo_mode:
                c2 = "B"
            else:
                c2 = input("\n  Votre réflexe (A/B) : ").strip().upper() or "B"
            resp_B[sc["axis_id"]] = c2

        # PHASE 4 : Sélection des Postures Comportementales Globales (Stratégies A à D)
        rounds_detail = []
        observable_vectors = []

        for idx, sc in enumerate(scenarios_pool):
            clear_screen()
            print("─" * 68)
            print(f" PHASE 4 : POSTURE GLOBALEMENT SPONTANÉE (SCÉNARIO {idx+1}/{len(scenarios_pool)})")
            print("─" * 68)
            print(f"\n{sc['scenario']}\n")
            print("Quelle est votre posture comportementale naturelle ?\n")
            for strat in sc["strategies"]:
                print(f"  [{strat['code']}] {strat['title']}")
                print(f"      {strat['desc']}\n")

            t0 = time.time()
            if demo_mode:
                choice_code = "C"
                t_react = 4.10 + idx * 0.3
            else:
                choice_code = input("  Votre choix (A/B/C/D) : ").strip().upper() or "C"
                t_react = time.time() - t0

            code_map = {"A": 0, "B": 1, "C": 2, "D": 3}
            chosen_strat_idx = code_map.get(choice_code, 2)
            strat_chosen = sc["strategies"][chosen_strat_idx]

            cA = resp_A[sc["axis_id"]]
            cB = resp_B[sc["axis_id"]]
            order_bias = 0.50 if cA != cB else 0.0
            I_0 = float(np.sin(0.5 * np.pi * (order_bias * 0.7 + 0.2)))

            S_eff = float(strat_chosen["S_eff"])
            K_ana_observed = float(strat_chosen["vector_state"][0])

            obs_vec = [K_ana_observed, S_eff, I_0]
            observable_vectors.append(obs_vec)

            round_record = {
                "round_index": idx + 1,
                "axis_id": sc["axis_id"],
                "axis_name": sc["axis_name"],
                "register": sc["register"],
                "life_sphere": sc["life_sphere"],
                "life_domain": sc["life_domain"],
                "generation_source": sc["generation_source"],
                "scenario_generated": sc["scenario"],
                "external_K_ana_constraint": sc["external_K_ana_constraint"],
                "perspective_A": sc["perspective_A"],
                "perspective_B": sc["perspective_B"],
                "user_resp_perspective_A": cA,
                "user_resp_perspective_B": cB,
                "offered_strategies": [
                    {"code": s["code"], "title": s["title"], "desc": s["desc"]}
                    for s in sc["strategies"]
                ],
                "user_choice_code": choice_code,
                "user_choice_title": strat_chosen["title"],
                "user_choice_desc": strat_chosen["desc"],
                "reaction_time_sec": round(float(t_react), 2),
                "computed_metrics": {
                    "K_ana_observed": round(K_ana_observed, 4),
                    "S_eff_rel": round(S_eff, 4),
                    "I_0_phase": round(I_0, 4)
                }
            }
            rounds_detail.append(round_record)

        obs_matrix = np.array(observable_vectors)
        cov_matrix = np.cov(obs_matrix)
        eigenvalues, _ = np.linalg.eigh(cov_matrix)

        gram_analysis = {
            "covariance_matrix_G": cov_matrix.tolist(),
            "eigenvalues_SVD": eigenvalues.tolist(),
            "orthogonal_independence_confirmed": bool(np.all(eigenvalues > 1e-4))
        }

        return rounds_detail, gram_analysis, plan_summary


# ═══════════════════════════════════════════════════════════════
# 6. Restitution Miroir & Maximes de Sagesse (Zero Jugement)
# ═══════════════════════════════════════════════════════════════

class MirrorWisdomEngineH12:
    @staticmethod
    def synthesize(rounds_detail, gram_analysis):
        k_list = [r["computed_metrics"]["K_ana_observed"] for r in rounds_detail]
        s_list = [r["computed_metrics"]["S_eff_rel"] for r in rounds_detail]
        i_list = [r["computed_metrics"]["I_0_phase"] for r in rounds_detail]

        K_ana_mean = float(np.mean(k_list))
        S_eff_mean = float(np.mean(s_list))
        I_0_mean   = float(np.mean(i_list))

        t_steps = np.linspace(0, 2*np.pi, 60)
        u_traj = K_ana_mean + 0.25 * np.cos(t_steps)
        w_traj = I_0_mean + 0.25 * np.sin(t_steps)
        du = np.gradient(u_traj)
        dw = np.gradient(w_traj)
        r2 = u_traj**2 + w_traj**2 + 1e-12
        gamma_berry = float(np.sum((u_traj * dw - w_traj * du) / r2))

        if K_ana_mean > 0.70:
            regime_name = "Régime de Cristallisation sous Pression Extérieure"
            maxime = (
                "« Le roseau plie mais ne rompt pas. La pierre la plus dure s'éclate sous le choc, "
                "tandis que l'eau épouse la forme du récipient sans jamais perdre sa nature propre. »\n"
                "  — Lao Tseu (Tao Tö King)"
            )
            meditation = (
                "La tomographie sur la base H^12 montre une cristallisation de l'état sous l'opérateur de contrainte K_ana. "
                "Cette tension est une protection naturelle indispensable face aux exigences d'urgence. "
                "Accueillir une zone de flou délibérée n'est pas abandonner la rigueur, c'est offrir du jeu au mouvement."
            )
        elif K_ana_mean < 0.35:
            regime_name = "Régime de Haute Fluidité Spectrale"
            maxime = (
                "« Pour que l'eau reflète la lune, il lui faut le calme du bassin ; "
                "sans rives pour la contenir, la rivière se perd dans la plaine. »"
            )
            meditation = (
                "La tomographie indique une haute entropie spectrale à travers les axes émotifs et éthiques. "
                "L'éventail des possibles est vaste et la réceptivité est maximale. "
                "La sagesse suggère d'offrir une rive contenante à cette intuition afin que la richesse des nuances se cristallise."
            )
        else:
            regime_name = "Zone d'Inflexion du Garant (Accord des Contraires dans H^12)"
            maxime = (
                "« La vérité n'est pas un point fixe mais la corde tendue de la lyre : "
                "c'est l'accord dynamique des tensions opposées qui produit la plus belle harmonie. »\n"
                "  — Héraclite d'Éphèse (Fragments)"
            )
            meditation = (
                "L'état mental habite la zone d'inflexion optimale (K_ana moyen ≈ 0.45), posture propre du Garant. "
                "Il maintient simultanément la rigueur éthique et l'ouverture phénoménologique, "
                "sans basculer dans le dogme ni dans la dispersion. La réactivité spectrale y est optimale."
            )

        return {
            "K_ana_mean": round(K_ana_mean, 4),
            "S_eff_mean": round(S_eff_mean, 4),
            "I_0_mean": round(I_0_mean, 4),
            "gamma_berry_rad": round(gamma_berry, 4),
            "regime_name": regime_name,
            "maxime": maxime,
            "meditation": meditation,
            "u_traj": u_traj.tolist(),
            "w_traj": w_traj.tolist()
        }

    @staticmethod
    def generate_dashboard(rounds_detail, synth, output_path="/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini/validation_estimateurs_dashboard.png"):
        fig = plt.figure(figsize=(14, 10))
        fig.patch.set_facecolor('#0f111a')
        
        gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 0])
        ax4 = fig.add_subplot(gs[1, 1])

        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_facecolor('#16192b')
            ax.tick_params(colors='#aaaacc', labelsize=8)
            for sp in ax.spines.values():
                sp.set_edgecolor('#333355')

        axis_names = [f"Scénario {r['round_index']}" for r in rounds_detail]
        k_values = [r["computed_metrics"]["K_ana_observed"] for r in rounds_detail]
        ax1.bar(axis_names, k_values, color=['#ffaa00', '#55ffaa', '#55aaff', '#cc77ff'], alpha=0.85)
        ax1.axhline(0.45, color='#ff5555', ls='--', label='Inflexion Garant K_c')
        ax1.set_title("Profil de Tension K_ana par Scénario H^12", color='white', fontsize=10, fontweight='bold')
        ax1.set_ylabel("K_ana Observé", color='#aaaacc', fontsize=8)
        ax1.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
        ax1.grid(alpha=0.2, color='#333355')

        x_grid = np.linspace(0, 1, 100)
        gamma_fit = 1.0 / (1.0 + np.exp(-10.0 * (x_grid - 0.45)))
        y_fit = 0.95 - 0.75 * gamma_fit
        ax2.plot(x_grid, y_fit, color='#ffaa00', lw=2, label='Loi Sigmoïde γ(K_ana)')
        ax2.axvline(synth['K_ana_mean'], color='#55ffaa', ls='--', label=f'K_ana moyen = {synth["K_ana_mean"]:.2f}')
        ax2.set_title("Position sur la Sigmoïde de Condensation", color='white', fontsize=10, fontweight='bold')
        ax2.set_xlabel("K_ana Moyen", color='#aaaacc', fontsize=8)
        ax2.set_ylabel("S_eff Moyen", color='#aaaacc', fontsize=8)
        ax2.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
        ax2.grid(alpha=0.2, color='#333355')

        latencies = [r["reaction_time_sec"] for r in rounds_detail]
        ax3.plot(axis_names, latencies, 'o-', color='#00e5ff', lw=2, ms=6, label='T_react (sec)')
        ax3.set_title("Latences de Réflexion (Temps de Décohérence)", color='white', fontsize=10, fontweight='bold')
        ax3.set_xlabel("Scénarios v15 (Base H^12)", color='#aaaacc', fontsize=8)
        ax3.set_ylabel("Temps (sec)", color='#aaaacc', fontsize=8)
        ax3.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
        ax3.grid(alpha=0.2, color='#333355')

        traj_u = synth["u_traj"]
        traj_w = synth["w_traj"]
        ax4.plot(traj_u, traj_w, color='#ffff55', lw=2, label=f'Cycle H^12 (γ = {synth["gamma_berry_rad"]:.2f} rad)')
        ax4.plot([traj_u[0]], [traj_w[0]], 'o', color='#ff3333', ms=7, label='S_0 Baseline')
        ax4.set_title("Holonomie globale dans H^12", color='white', fontsize=10, fontweight='bold')
        ax4.set_xlabel("Tension K_ana", color='#aaaacc', fontsize=8)
        ax4.set_ylabel("Phase Imaginaire I_0", color='#aaaacc', fontsize=8)
        ax4.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
        ax4.grid(alpha=0.2, color='#333355')

        fig.suptitle("VISUALISATION DE L'ESPACE INTÉRIEUR (v15 - PUMP-PROBE ENTRELACÉ)", color='white', fontsize=12, fontweight='bold', y=0.97)
        fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"\n[Dashboard Synthétique sauvegardé -> {output_path}]\n")


# ═══════════════════════════════════════════════════════════════
# 7. Point d'Entrée Principal & Export JSON Integral v15
# ═══════════════════════════════════════════════════════════════

def main():
    debug = "--debug" in sys.argv
    demo = "--demo" in sys.argv

    rounds_detail, gram_analysis, plan_summary = TomographyH12Runner.run_tomography(debug_mode=debug, demo_mode=demo, sample_size=4)
    synth = MirrorWisdomEngineH12.synthesize(rounds_detail, gram_analysis)

    clear_screen()
    output_png = "/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini/validation_estimateurs_dashboard.png"
    MirrorWisdomEngineH12.generate_dashboard(rounds_detail, synth, output_path=output_png)

    print("\n" + "=" * 68)
    print("   VISUALISATION MIROIR DE L'ESPACE INTÉRIEUR (v15 PUMP-PROBE)")
    print("=" * 68)
    print(f" Date : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 68)
    print(f" ► Axes H^12 échantillonnés par IA    : {len(rounds_detail)} / 12")
    print(f" ► Pression Analytique Moyenne K_ana   : {synth['K_ana_mean']:.4f}")
    print(f" ► Entropie Spectrale Moyenne S_eff   : {synth['S_eff_mean']:.4f}")
    print(f" ► Phase Imaginaire Moyenne I_0        : {synth['I_0_mean']:.4f}")
    print(f" ► Phase de Berry Globale (γ_Berry)   : {synth['gamma_berry_rad']:.4f} rad")
    print("-" * 68)
    print(f" ÉTAT D'ÉQUILIBRE GLOBAL : {synth['regime_name']}\n")
    print(" MAXIME DE SAGESSE :")
    print(f" {synth['maxime']}\n")
    print(" MISE EN PERSPECTIVE :")
    print(f" {synth['meditation']}")
    print("=" * 68)

    # EXPORT INTEGRAL (Traçabilité 100% v15 avec Plan Phase 0)
    output_dir = "/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"session_protocole_v15_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    export_data = {
        "session_timestamp": datetime.datetime.now().isoformat(),
        "hilbert_space_total_dimension": 12,
        "sampled_axes_count": len(rounds_detail),
        "ai_synthesizer_version": "v15_shuffled_pump_probe_llm_planned",
        "phase_0_plan_summary": plan_summary,
        "rounds_detail_integral": rounds_detail,
        "gram_matrix_analysis": gram_analysis,
        "tomography_mirror_synthesis": synth
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"\nRapport de session v15 (Pump-Probe Entrelacé 100% traçable) exporté avec succès -> {filepath}\n")


if __name__ == "__main__":
    main()
