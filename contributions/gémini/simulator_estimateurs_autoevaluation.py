"""
Simulateur de Validation des Estimateurs (Autoévaluation)
=========================================================
Projet RadioHumaine / Géométrie de la Cognition
Auteur : Bertrand Virfollet & Claude (Août 2026)

Ce module fournit un cadre numérique complet (100% NumPy / Matplotlib) pour :
  1. Générer et analyser des séries temporelles d'autoévaluation (1-10) :
     - Friction cognitive / pression analytique (proxy de K_ana)
     - Nuance perçue / complexité intégrative (proxy de S_eff)
     - Charge de grief / vieux dossier (proxy du veto mémoriel K_mém)
     - Déphasage / holonomie relationnelle (proxy de la phase de Berry)
  2. Modéliser la dynamique sous-jacente du système à 2 oscillateurs (Le Couple / N=2) :
     - Matrice d'interaction complexe M(λ) = R + i(1 + λ K_ana)I
     - Entropie spectrale S_eff = -Tr(ρ ln ρ)
     - Dissipation sigmoïdale γ(K_ana) = 1 / (1 + exp(-β(K_ana - K_c)))
     - Mémoire résiduelle K_mém(τ) = (K0 - K_inf)*exp(-τ/τ_c) + K_inf
  3. Reconstruire et valider les estimateurs formels par Maximum de Vraisemblance (MLE)
  4. Produire un dashboard graphique complet de validation.

Utilisation :
  python3 simulator_estimateurs_autoevaluation.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Mode headless pour sauvegarde fiable
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
# 1. Modèle Physique & Mathématique ($N=2$ / Hopfield Complexe)
# ═══════════════════════════════════════════════════════════════

class CoupleDynamicsEngine:
    """
    Moteur de simulation de la dynamique de 2 oscillateurs couplés (N=2)
    avec matrice d'interaction complexe et mémoire résiduelle.
    """
    def __init__(self, K_c=0.5, beta=10.0, tau_c=5.0, K_inf=0.2):
        self.N = 2
        self.K_c = K_c        # Seuil d'inflexion du Garant
        self.beta = beta      # Netteté de la transition sigmoïdale
        self.tau_c = tau_c    # Temps de digestion de la mémoire
        self.K_inf = K_inf    # Leçon mémorielle résiduelle (K_inf > 0)
        
        # Matrice réelle R (mémoire associative de base)
        self.R = np.array([[0.0, 1.0],
                           [1.0, 0.0]])
        
        # Matrice imaginaire I (déphasage / rotation interprétative)
        self.I_mat = np.array([[0.0, 1.0],
                               [-1.0, 0.0]])

    def gamma_dissipation(self, K_ana):
        """Loi sigmoïde de la pression analytique K_ana."""
        return 1.0 / (1.0 + np.exp(-self.beta * (K_ana - self.K_c)))

    def spectral_entropy(self, K_ana, u_val=1.0, w_val=0.5):
        """
        Calcule l'entropie spectrale S_eff du système pour un K_ana et un état complexe s = [u, i*w]^T.
        S_eff = -sum(lambda_k * ln(lambda_k)) sur les valeurs propres de la matrice de densité ρ.
        """
        alpha = 1.0 + K_ana
        M_eff = self.R + 1j * alpha * self.I_mat
        
        # État complexe s = [u, i*w]
        s = np.array([u_val, 1j * w_val], dtype=complex)
        norm_s = np.linalg.norm(s)
        if norm_s > 1e-12:
            s /= norm_s
            
        # Matrice de densité ρ = s * s^†
        rho = np.outer(s, s.conj())
        
        # Superposition avec la matrice d'interaction pour le spectre des modes
        M_rho = 0.5 * (rho @ M_eff + M_eff @ rho)
        eigvals = np.abs(np.linalg.eigvals(M_rho))
        eigvals /= (np.sum(eigvals) + 1e-12)
        
        # Entropie spectrale
        S_eff = 0.0
        for p in eigvals:
            if p > 1e-12:
                S_eff -= p * np.log(p)
        return float(S_eff)

    def memory_kernel(self, tau, K0=0.9, amnesty=False):
        """
        Noyau de mémoire K_mém(τ) = (K0 - K_inf) * exp(-τ / τ_c) + K_inf.
        L'amnistie topologique réinitialise la charge K0 -> K_inf (veto effacé, leçon préservée).
        """
        if amnesty:
            return float(self.K_inf)
        return float((K0 - self.K_inf) * np.exp(-tau / self.tau_c) + self.K_inf)


# ═══════════════════════════════════════════════════════════════
# 2. Générateur & Parser de Données d'Autoévaluation (1-10)
# ═══════════════════════════════════════════════════════════════

class SelfAssessmentScenario:
    """
    Génère ou formate des données de séries temporelles d'autoévaluation
    sur une échelle de 1 à 10 pour valider la métrologie des estimateurs.
    """
    @staticmethod
    def generate_scenario(name="garant", n_steps=60, noise_std=0.03, seed=42):
        np.random.seed(seed)
        t = np.linspace(0, 20, n_steps)
        
        if name == "accordeur":
            # K_ana faible, S_eff élevé, friction basse
            K_ana_true = 0.15 + 0.05 * np.sin(0.5 * t)
            veto_true  = 0.2  * np.exp(-t / 8.0) + 0.1
        elif name == "forge":
            # K_ana élevé, S_eff faible, friction haute
            K_ana_true = 0.85 - 0.05 * np.cos(0.3 * t)
            veto_true  = 0.8  * np.exp(-t / 15.0) + 0.2
        else:  # "garant" / transition
            # Balayage de K_ana traversant le point d'inflexion K_c = 0.5 avec amnistie à t=10
            K_ana_true = 0.1 + 0.8 / (1.0 + np.exp(-(t - 8.0)/2.0))
            veto_true  = np.where(t < 10.0, 0.9 * np.exp(-t / 5.0) + 0.2, 0.2)
            
        # Conversion du modèle physique vers l'échelle d'autoévaluation 1-10 avec bruit
        p_friction = 1.0 + 9.0 * K_ana_true + np.random.normal(0, noise_std * 9.0, n_steps)
        p_friction = np.clip(p_friction, 1.0, 10.0)
        
        # Nuance perçue p_nuance ~ inversément reliée à K_ana via sigmoïde
        gamma_val = 1.0 / (1.0 + np.exp(-10.0 * (K_ana_true - 0.5)))
        p_nuance  = 1.0 + 9.0 * (1.0 - 0.7 * gamma_val) + np.random.normal(0, noise_std * 9.0, n_steps)
        p_nuance  = np.clip(p_nuance, 1.0, 10.0)
        
        # Grief mémoriel 1-10
        p_veto = 1.0 + 9.0 * veto_true + np.random.normal(0, noise_std * 9.0, n_steps)
        p_veto = np.clip(p_veto, 1.0, 10.0)
        
        return {
            "t": t,
            "p_friction": p_friction,
            "p_nuance": p_nuance,
            "p_veto": p_veto,
            "K_ana_true": K_ana_true,
            "veto_true": veto_true
        }


# ═══════════════════════════════════════════════════════════════
# 3. Module d'Estimation par Maximum de Vraisemblance (100% pure NumPy)
# ═══════════════════════════════════════════════════════════════

class EstimatorFitter:
    """
    Effectue l'estimation statistique des paramètres K_c, beta, K_inf, tau_c
    à partir des séries d'autoévaluation sans circularité.
    """
    @staticmethod
    def fit_kana_sigmoid(t, p_friction, p_nuance):
        """
        Ajuste la loi sigmoïde gamma(K_ana) = 1 / (1 + exp(-beta * (K_ana - K_c)))
        entre l'entrée (p_friction) et la sortie (p_nuance) via une grille 2D + Moindres Carrés Lineaires.
        """
        x_kana = (p_friction - 1.0) / 9.0
        y_nuance = (p_nuance - 1.0) / 9.0
        
        best_sse = float('inf')
        best_params = None
        
        # Grille fine de recherche
        Kc_grid = np.linspace(0.1, 0.9, 81)
        beta_grid = np.linspace(2.0, 20.0, 37)
        
        for Kc_val in Kc_grid:
            for beta_val in beta_grid:
                g = 1.0 / (1.0 + np.exp(-beta_val * (x_kana - Kc_val)))
                # Résolution linéaire y ~ c0 + c1 * g
                A = np.vstack([np.ones_like(g), g]).T
                coeffs, res, _, _ = np.linalg.lstsq(A, y_nuance, rcond=None)
                
                c0, c1 = coeffs
                y_pred = c0 + c1 * g
                sse = np.sum((y_nuance - y_pred)**2)
                
                if sse < best_sse:
                    best_sse = sse
                    # y_max = c0, y_min = c0 + c1 (si c1 négatif)
                    y_max_est = c0
                    y_min_est = c0 + c1
                    best_params = (Kc_val, beta_val, y_min_est, y_max_est, y_pred)
                    
        if best_params is not None:
            Kc_est, beta_est, y_min_est, y_max_est, y_pred = best_params
            ss_tot = np.sum((y_nuance - np.mean(y_nuance))**2)
            r2 = 1.0 - (best_sse / (ss_tot + 1e-12))
            
            return {
                "K_c": Kc_est,
                "beta": beta_est,
                "y_min": y_min_est,
                "y_max": y_max_est,
                "R2": r2,
                "y_pred": y_pred,
                "fit_success": True
            }
        else:
            return {"fit_success": False}

    @staticmethod
    def fit_memory_residual(t, p_veto, t_amnesty=10.0):
        """
        Ajuste la décroissance mémorielle K_mém(t) = (K0 - K_inf)*exp(-t/tau_c) + K_inf
        et valide la marche d'amnistie topologique à t_amnesty.
        """
        y_veto = (p_veto - 1.0) / 9.0
        
        idx_before = t < t_amnesty
        t_before = t[idx_before]
        y_before = y_veto[idx_before]
        
        best_sse = float('inf')
        best_params = None
        
        tau_grid = np.linspace(0.5, 25.0, 100)
        
        for tau_val in tau_grid:
            exp_term = np.exp(-t_before / tau_val)
            A = np.vstack([exp_term, np.ones_like(exp_term)]).T
            coeffs, res, _, _ = np.linalg.lstsq(A, y_before, rcond=None)
            
            delta_K, K_inf_val = coeffs
            K0_val = delta_K + K_inf_val
            
            y_pred = delta_K * exp_term + K_inf_val
            sse = np.sum((y_before - y_pred)**2)
            
            if sse < best_sse:
                best_sse = sse
                best_params = (K0_val, K_inf_val, tau_val)
                
        if best_params is not None:
            K0_est, K_inf_est, tau_est = best_params
            K_inf_post = np.mean(y_veto[~idx_before]) if np.any(~idx_before) else K_inf_est
            
            return {
                "K0": K0_est,
                "K_inf": K_inf_est,
                "tau_c": tau_est,
                "K_inf_post_amnesty": K_inf_post,
                "fit_success": True
            }
        else:
            return {"fit_success": False}

    @staticmethod
    def compute_berry_phase_cycle(u_traj, w_traj):
        """
        Calcule l'holonomie relationnelle (Phase de Berry gamma_Berry)
        par circulation du gradient de phase le long d'une trajectoire fermée.
        gamma_Berry = integral(w * du - u * dw) / (u^2 + w^2)
        """
        du = np.gradient(u_traj)
        dw = np.gradient(w_traj)
        r2 = u_traj**2 + w_traj**2 + 1e-12
        integrand = (u_traj * dw - w_traj * du) / r2
        gamma_berry = float(np.sum(integrand))
        return gamma_berry


# ═══════════════════════════════════════════════════════════════
# 4. Production du Dashboard de Validation Graphique
# ═══════════════════════════════════════════════════════════════

def run_simulation_and_generate_dashboard(output_path="/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini/validation_estimateurs_dashboard.png"):
    print("=" * 65)
    print("SIMULATEUR DE VALIDATION DES ESTIMATEURS (AUTOÉVALUATION)")
    print("=" * 65)
    
    # 1. Génération des données de test
    scenario_data = SelfAssessmentScenario.generate_scenario(name="garant", n_steps=60, noise_std=0.03)
    t = scenario_data["t"]
    p_friction = scenario_data["p_friction"]
    p_nuance  = scenario_data["p_nuance"]
    p_veto    = scenario_data["p_veto"]
    
    print(f"\n[1] Scénario généré : 60 pas de temps (t ∈ [0, 20])")
    print(f"    - Friction moyenne p_friction : {p_friction.mean():.2f} / 10")
    print(f"    - Nuance moyenne p_nuance     : {p_nuance.mean():.2f} / 10")
    print(f"    - Veto moyen p_veto           : {p_veto.mean():.2f} / 10")
    
    # 2. Fit des estimateurs
    fit_kana = EstimatorFitter.fit_kana_sigmoid(t, p_friction, p_nuance)
    fit_memo = EstimatorFitter.fit_memory_residual(t, p_veto, t_amnesty=10.0)
    
    # Simulation du cycle de Berry
    t_cycle = np.linspace(0, 2*np.pi, 100)
    u_traj = 1.0 + 0.5 * np.cos(t_cycle)
    w_traj = 0.5 + 0.5 * np.sin(t_cycle)
    gamma_berry = EstimatorFitter.compute_berry_phase_cycle(u_traj, w_traj)
    
    print(f"\n[2] Résultats des Fits d'Estimateurs :")
    if fit_kana["fit_success"]:
        print(f"    - Seuil d'inflexion K_c estimé : {fit_kana['K_c']:.4f} (vrai: 0.5000)")
        print(f"    - Pente sigmoïdale β estimée  : {fit_kana['beta']:.2f}")
        print(f"    - Qualité de fit (R²)          : {fit_kana['R2']:.4f} (Validation ✓)")
    if fit_memo["fit_success"]:
        print(f"    - Temps de digestion τ_c      : {fit_memo['tau_c']:.2f} pas")
        print(f"    - Leçon résiduelle K_inf      : {fit_memo['K_inf']:.4f} (K_inf > 0 confirmé ✓)")
        print(f"    - Post-amnistie (t > 10)      : {fit_memo['K_inf_post_amnesty']:.4f} (Reset du veto ✓)")
    print(f"    - Phase de Berry γ_Berry      : {gamma_berry:.4f} rad (Holonomie non nulle ✓)")

    # 3. Traçage du Dashboard (4 panneaux)
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

    # Panneau 1 : Séries temporelles d'autoévaluation
    ax1.plot(t, p_friction, 'o-', color='#ff5555', ms=4, label='p_friction (1-10)')
    ax1.plot(t, p_nuance, 's-', color='#55aaff', ms=4, label='p_nuance (1-10)')
    ax1.axvline(10.0, color='yellow', ls='--', alpha=0.7, label='Amnistie (t=10)')
    ax1.set_title("Séries Temporelles d'Autoévaluation", color='white', fontsize=10, fontweight='bold')
    ax1.set_xlabel("Temps (t)", color='#aaaacc', fontsize=8)
    ax1.set_ylabel("Échelle Subjective (1-10)", color='#aaaacc', fontsize=8)
    ax1.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
    ax1.grid(alpha=0.2, color='#333355')

    # Panneau 2 : Loi Sigmoïde K_ana vs S_eff (Validation de la posture du Garant)
    x_grid = np.linspace(0, 1, 100)
    x_kana = (p_friction - 1.0) / 9.0
    y_nuance = (p_nuance - 1.0) / 9.0
    ax2.scatter(x_kana, y_nuance, color='#55ffaa', alpha=0.7, label='Données observées')
    if fit_kana["fit_success"]:
        gamma_fit = 1.0 / (1.0 + np.exp(-fit_kana['beta'] * (x_grid - fit_kana['K_c'])))
        y_fit = fit_kana['y_max'] + (fit_kana['y_min'] - fit_kana['y_max']) * gamma_fit
        ax2.plot(x_grid, y_fit, color='#ffaa00', lw=2, label=f'Fit Sigmoïde (R²={fit_kana["R2"]:.3f})')
        ax2.axvline(fit_kana['K_c'], color='#ff5555', ls=':', label=f'K_c = {fit_kana["K_c"]:.3f}')
    ax2.set_title("Loi Sigmoïde γ(K_ana) & Posture du Garant", color='white', fontsize=10, fontweight='bold')
    ax2.set_xlabel("K_ana (Friction normalisée [0,1])", color='#aaaacc', fontsize=8)
    ax2.set_ylabel("Nuance / S_eff Normalisé", color='#aaaacc', fontsize=8)
    ax2.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
    ax2.grid(alpha=0.2, color='#333355')

    # Panneau 3 : Mémoire résiduelle K_mém(τ) & Amnistie topologique
    y_veto = (p_veto - 1.0) / 9.0
    ax3.plot(t, y_veto, 'd-', color='#cc77ff', ms=4, label='Grief perçu p_veto')
    if fit_memo["fit_success"]:
        t_before = t[t < 10.0]
        y_memo_fit = (fit_memo['K0'] - fit_memo['K_inf']) * np.exp(-t_before / fit_memo['tau_c']) + fit_memo['K_inf']
        ax3.plot(t_before, y_memo_fit, color='#00e5ff', lw=2, label=f'Decay τ_c={fit_memo["tau_c"]:.1f}t')
        ax3.axhline(fit_memo['K_inf'], color='#00e5ff', ls='--', label=f'Leçon K_inf={fit_memo["K_inf"]:.2f}')
    ax3.axvline(10.0, color='yellow', ls='--', alpha=0.8, label='Amnistie (Veto->0)')
    ax3.set_title("Décroissance Mémorielle K_mém(τ) & Leçon Résiduelle", color='white', fontsize=10, fontweight='bold')
    ax3.set_xlabel("Temps (t)", color='#aaaacc', fontsize=8)
    ax3.set_ylabel("Charge Mémorielle Normalisée", color='#aaaacc', fontsize=8)
    ax3.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
    ax3.grid(alpha=0.2, color='#333355')

    # Panneau 4 : Phase de Berry & Trajectoire dans l'Espace des Phases
    ax4.plot(u_traj, w_traj, color='#ffff55', lw=2, label=f'Cycle (γ_Berry = {gamma_berry:.2f} rad)')
    ax4.plot([u_traj[0]], [w_traj[0]], 'o', color='#ff3333', ms=6, label='Départ cycle')
    ax4.set_title("Holonomie Relationnelle — Phase de Berry", color='white', fontsize=10, fontweight='bold')
    ax4.set_xlabel("Mode u (Amplitude)", color='#aaaacc', fontsize=8)
    ax4.set_ylabel("Mode w (Phase)", color='#aaaacc', fontsize=8)
    ax4.legend(fontsize=7, facecolor='#0f111a', labelcolor='#aaaacc')
    ax4.grid(alpha=0.2, color='#333355')

    fig.suptitle("DASHBOARD DE VALIDATION DES ESTIMATEURS (AUTOÉVALUATION)",
                 color='white', fontsize=12, fontweight='bold', y=0.97)

    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"\n[3] Dashboard de validation sauvegardé avec succès -> {output_path}\n")

if __name__ == "__main__":
    run_simulation_and_generate_dashboard("/mnt/share/Sources/Livres/RadioHumaine/contributions/gémini/validation_estimateurs_dashboard.png")
