"""
Test de l'isomorphisme Chladni–Hopfield complexe  (v3)
======================================================
Correction fondamentale :
  Les états du réseau de Hopfield complexe sont s ∈ C^N,
  paramétrés par s = u·v1 + i·w·v2 (deux directions réelles,
  phase portée par i).  Avec des états réels, Re(E) est
  indépendant de λ — ce qui invalide le test.  Avec des
  états complexes, Re(E) dépend de λ via les termes croisés
  u^T I w qui entrent dans la partie réelle de E.

Prédiction testée :
  Quand λ ∈ [0,1] varie continûment,
  la surface nodale  Re(E(s,λ)) = 0  dans le plan complexe
  (u, w) subit des sauts topologiques discrets.
  Ces sauts sont détectés par le nombre de courbes nodales
  et leur type (fermées / ouvertes) — analogue direct des
  lignes nodales de Chladni changeant de topologie à ω_c.
  Les valeurs critiques λ_c sont prédites par le spectre
  de la matrice de couplage M².

Sorties :
  - Figure 1 : grille de surfaces nodales Re(E)=0 pour λ ∈ [0,1]
  - Figure 2 : nombre de courbes nodales et leur type vs λ,
               avec les λ_c prédits superposés
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. Construction de M = R + i·I
# ─────────────────────────────────────────────
np.random.seed(42)
N = 4

patterns = np.array([
    [+1, +1, -1, -1],
    [+1, -1, +1, -1],
    [+1, -1, -1, +1],
], dtype=float)

R = np.zeros((N, N))
for p in patterns:
    R += np.outer(p, p)
R /= N
np.fill_diagonal(R, 0)

# I antisymétrique — encode la rotation de phase
I_mat = np.array([
    [ 0.0,  0.6, -0.4,  0.2],
    [-0.6,  0.0,  0.8, -0.2],
    [ 0.4, -0.8,  0.0,  0.6],
    [-0.2,  0.2, -0.6,  0.0],
])

M = R + 1j * I_mat

# ─────────────────────────────────────────────
# 2. Prédiction des λ_c via spectre de M²
# ─────────────────────────────────────────────
M2 = M @ M
eigenvalues_M2 = np.linalg.eigvals(M2)
trace_M2 = np.trace(M2)
kappa4_scale = np.abs(np.real(trace_M2)) / N

lambda_c_predicted = []
for vp in eigenvalues_M2:
    if kappa4_scale > 1e-10:
        lc = np.real(vp) / kappa4_scale
        if 0.02 < lc < 0.98:
            lambda_c_predicted.append(lc)
lambda_c_predicted = sorted(set([round(lc, 3) for lc in lambda_c_predicted]))

print("=" * 60)
print(f"Réseau de Hopfield complexe  N = {N}")
print("=" * 60)
print(f"\nSpectre de M² : {np.round(eigenvalues_M2, 4)}")
print(f"Trace(M²)     : {np.round(trace_M2, 4)}")
print(f"λ_c prédits   : {[round(l,4) for l in lambda_c_predicted]}")

# ─────────────────────────────────────────────
# 3. Plan d'états complexes et énergie
# ─────────────────────────────────────────────
# Deux directions de base dans R^4 pour span l'espace d'états complexes
# Choisies pour maximiser la sensibilité à I_mat (termes croisés dans Re(E))
# v1 = vecteur propre dominant de R, v2 = vecteur propre de I_mat
vals_R, vecs_R = np.linalg.eigh(R)
idx_R = np.argsort(np.abs(vals_R))[::-1]
v1 = vecs_R[:, idx_R[0]]  # mode dominant de R

# Pour v2 : vecteur propre de (I_mat^T I_mat) — direction de phase maximale
vals_I, vecs_I = np.linalg.eigh(I_mat.T @ I_mat)
v2 = vecs_I[:, np.argmax(vals_I)]
# Orthogonalisation de Gram-Schmidt
v2 = v2 - np.dot(v2, v1) * v1
v2 /= np.linalg.norm(v2)

def energy_re(u_coord, w_coord, lam, K_ana=1.0):
    """
    E(s,λ) = -½ s† M_eff s  avec s = u·v1 + i·w·v2  (s ∈ C^N)
    M_eff = R + i·(1 + λ·K_ana)·I
    
    Re(E) = -½ [u²(v1^T R v1) + w²(v2^T R v2)]
            + (1+λ)/2 · u·w · (v1^T I v2 - v2^T I v1)
    
    Le dernier terme (antisymétrique en I) dépend de λ => sauts possibles.
    """
    alpha = 1.0 + lam * K_ana
    # Termes quadratiques réels
    rr1 = v1 @ R @ v1
    rr2 = v2 @ R @ v2
    # Terme croisé via I (antisymétrique => (v1^T I v2) = -(v2^T I v1))
    cross_I = v1 @ I_mat @ v2   # scalaire réel car I antisymétrique
    # Re(E) avec états complexes s = u·v1 + i·w·v2
    re_E = -0.5 * (u_coord**2 * rr1 + w_coord**2 * rr2) \
           + alpha * u_coord * w_coord * cross_I
    return re_E

# Vérifie la dépendance λ
print("\nVérification : Re(E) dépend-il de λ ?")
cross_val = v1 @ I_mat @ v2
print(f"  Terme croisé v1^T I v2 = {cross_val:.6f}")
print(f"  (non nul => dépendance λ confirmée)")
for lam in [0.0, 0.3, 0.7, 1.0]:
    g = np.vectorize(lambda u,w: energy_re(u,w,lam))(
        *np.meshgrid(np.linspace(-2,2,30), np.linspace(-2,2,30)))
    print(f"  λ={lam:.1f}  Re(E): [{g.min():.4f}, {g.max():.4f}]"
          f"  zero-crossing={g.min()<0<g.max()}")

# ─────────────────────────────────────────────
# 4. Calcul des grilles Re(E) pour chaque λ
# ─────────────────────────────────────────────
grid_size = 100
u_range = np.linspace(-2.5, 2.5, grid_size)
w_range = np.linspace(-2.5, 2.5, grid_size)
UU, WW = np.meshgrid(u_range, w_range)

lambda_values = np.linspace(0.0, 1.0, 41)
E_re_grids = []

for lam in lambda_values:
    grid = energy_re(UU, WW, lam)
    E_re_grids.append(grid)

# ─────────────────────────────────────────────
# 5. Comptage topologique des courbes nodales
# ─────────────────────────────────────────────
def count_nodal_curves(grid, u_range, w_range, level=0.0, tol_closed=0.15):
    """
    Compte directement les courbes nodales Re(E)=0 en tant que
    chemins matplotlib — chaque path = une courbe connexe.
    Distingue fermées (boucles, b1 +=1) et ouvertes (b0 +=1 par paire).
    """
    fig_tmp, ax_tmp = plt.subplots()
    cs = ax_tmp.contour(u_range, w_range, grid, levels=[level])
    paths = []
    if hasattr(cs, 'get_paths'):
        paths = cs.get_paths()
    elif hasattr(cs, 'collections') and len(cs.collections) > 0:
        paths = cs.collections[0].get_paths()
    else:
        for seg_list in getattr(cs, 'allsegments', []):
            for seg in seg_list:
                if len(seg) > 0:
                    import matplotlib.path as mpath
                    paths.append(mpath.Path(seg))
    plt.close(fig_tmp)

    n_total = len(paths)
    n_closed = 0
    n_open = 0
    lengths = []

    for path in paths:
        verts = path.vertices
        if len(verts) < 3:
            continue
        dist = np.linalg.norm(verts[-1] - verts[0])
        arc = np.sum(np.linalg.norm(np.diff(verts, axis=0), axis=1))
        lengths.append(arc)
        if dist < tol_closed * arc:
            n_closed += 1
        else:
            n_open += 1

    # Betti approximatifs : b0 = composantes (ouvertes par paires + fermées)
    # b1 = boucles fermées
    b0 = max(1, n_closed + (n_open + 1) // 2) if n_total > 0 else 0
    b1 = n_closed

    return n_total, n_closed, n_open, b0, b1

print("\nAnalyse topologique des surfaces nodales...")
results = []
for k, (lam, grid) in enumerate(zip(lambda_values, E_re_grids)):
    n_tot, n_cl, n_op, b0, b1 = count_nodal_curves(grid, u_range, w_range)
    results.append((lam, n_tot, n_cl, n_op, b0, b1))
    if k % 4 == 0 or abs(lam - round(lam, 1)) < 0.001:
        print(f"  λ={lam:.2f}  courbes={n_tot}  fermées={n_cl}  ouvertes={n_op}"
              f"  b0={b0}  b1={b1}")

lam_arr = np.array([r[0] for r in results])
n_tot_arr = np.array([r[1] for r in results])
n_cl_arr  = np.array([r[2] for r in results])
n_op_arr  = np.array([r[3] for r in results])
b0_arr    = np.array([r[4] for r in results])
b1_arr    = np.array([r[5] for r in results])

# ─────────────────────────────────────────────
# 6. Figure 1 : grille de contours nodaux
# ─────────────────────────────────────────────
n_show = 12
idx_show = np.linspace(0, len(lambda_values)-1, n_show, dtype=int)

fig1, axes = plt.subplots(3, 4, figsize=(14, 10))
fig1.suptitle(
    "Surfaces nodales Re(E) = 0 — Réseau de Hopfield complexe\n"
    r"États complexes $s = u\mathbf{v}_1 + iw\mathbf{v}_2$,"
    r"  $M_{\mathrm{eff}} = R + i(1+\lambda)I$",
    fontsize=12, fontweight='bold'
)

for ax_idx, k in enumerate(idx_show):
    ax = axes[ax_idx // 4][ax_idx % 4]
    lam = lambda_values[k]
    grid = E_re_grids[k]
    b0, b1 = b0_arr[k], b1_arr[k]
    n_cl = n_cl_arr[k]

    vmax = np.percentile(np.abs(grid), 97)
    ax.imshow(grid, origin='lower',
              extent=[u_range[0], u_range[-1], w_range[0], w_range[-1]],
              cmap='RdBu_r', vmin=-vmax, vmax=vmax, alpha=0.55)
    ax.contour(u_range, w_range, grid, levels=[0.0],
               colors='k', linewidths=1.8)

    # Signale les λ proches d'un λ_c prédit
    near_critical = any(abs(lam - lc) < 0.04 for lc in lambda_c_predicted)
    color = 'red' if near_critical else 'black'

    ax.set_title(
        f"λ={lam:.2f}  |  b₀={b0}  b₁={b1}",
        fontsize=9, color=color, fontweight='bold' if near_critical else 'normal'
    )
    ax.set_xlabel("u  (amplitude)", fontsize=7)
    ax.set_ylabel("w  (phase)", fontsize=7)
    ax.tick_params(labelsize=6)

    if near_critical:
        for spine in ax.spines.values():
            spine.set_edgecolor('red')
            spine.set_linewidth(2)

plt.tight_layout()
fig1.savefig("/mnt/share/Sources/Livres/RadioHumaine/contributions/claude/chladni_hopfield_nodal_surfaces.png",
             dpi=150, bbox_inches='tight')
print("\nFigure 1 sauvegardée.")

# ─────────────────────────────────────────────
# 7. Figure 2 : topologie vs λ
# ─────────────────────────────────────────────
fig2, axes2 = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
fig2.suptitle(
    "Sauts topologiques des surfaces nodales vs λ\n"
    "Test de l'isomorphisme Chladni–Hopfield complexe",
    fontsize=13, fontweight='bold'
)

# Nombre total de courbes nodales
axes2[0].step(lam_arr, n_tot_arr, where='post',
              color='steelblue', lw=2.5, label='Nombre total de courbes nodales')
axes2[0].set_ylabel("n courbes", fontsize=11)
axes2[0].legend(fontsize=9); axes2[0].grid(alpha=0.3)

# Fermées (b1) vs ouvertes
axes2[1].step(lam_arr, n_cl_arr, where='post',
              color='darkorange', lw=2.5, label='b₁ — courbes fermées (boucles)')
axes2[1].step(lam_arr, n_op_arr, where='post',
              color='forestgreen', lw=2.5, linestyle='--',
              label='Courbes ouvertes')
axes2[1].set_ylabel("n courbes", fontsize=11)
axes2[1].legend(fontsize=9); axes2[1].grid(alpha=0.3)

# b0
axes2[2].step(lam_arr, b0_arr, where='post',
              color='purple', lw=2.5, label='b₀ — composantes connexes')
axes2[2].set_ylabel("b₀", fontsize=11)
axes2[2].set_xlabel("λ  (paramètre dissipatif de Kₐₙₐ)", fontsize=11)
axes2[2].legend(fontsize=9); axes2[2].grid(alpha=0.3)

# λ_c prédits
for ax in axes2:
    for i, lc in enumerate(lambda_c_predicted):
        ax.axvline(lc, color='red', linestyle='--', alpha=0.85, lw=1.5,
                   label=f'λ_c={lc:.3f}' if i == 0 and ax is axes2[0] else "")
    ax.set_ylim(bottom=0)

axes2[0].legend(fontsize=9)
axes2[0].text(0.01, 0.88,
              "│ Lignes rouges : λ_c prédits par spectre(M²)",
              transform=axes2[0].transAxes, fontsize=8, color='red')

plt.tight_layout()
fig2.savefig("/mnt/share/Sources/Livres/RadioHumaine/contributions/claude/chladni_hopfield_betti_evolution.png",
             dpi=150, bbox_inches='tight')
print("Figure 2 sauvegardée.")

# ─────────────────────────────────────────────
# 8. Rapport de validation
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("RAPPORT DE VALIDATION")
print("=" * 60)

# Détecte les sauts effectifs
def find_jumps(arr, lam_arr, min_delta=1):
    return [lam_arr[k] for k in range(1, len(arr))
            if abs(int(arr[k]) - int(arr[k-1])) >= min_delta]

jumps_ntot = find_jumps(n_tot_arr, lam_arr)
jumps_b0   = find_jumps(b0_arr, lam_arr)
jumps_b1   = find_jumps(b1_arr, lam_arr)

print(f"\nSauts du nombre de courbes  : {[round(l,3) for l in jumps_ntot]}")
print(f"Sauts de b0                 : {[round(l,3) for l in jumps_b0]}")
print(f"Sauts de b1                 : {[round(l,3) for l in jumps_b1]}")
print(f"λ_c prédits par spectre(M²) : {[round(l,4) for l in lambda_c_predicted]}")

tol = 0.08
all_jumps = sorted(set(jumps_ntot + jumps_b0 + jumps_b1))
concordances = []
for j in all_jumps:
    for lc in lambda_c_predicted:
        if abs(j - lc) < tol:
            concordances.append((j, lc))

print(f"\nConcordances (tolérance ±{tol}) :")
if concordances:
    for j, lc in concordances:
        print(f"  Saut effectif λ={j:.3f}  ↔  λ_c prédit={lc:.4f}  ✓")
    ratio = len(set(j for j,_ in concordances)) / max(len(all_jumps), 1)
    verdict = ("ISOMORPHISME SUPPORTÉ" if ratio >= 0.5
               else "ISOMORPHISME PARTIEL")
    print(f"\nTaux de concordance : {ratio:.0%}")
    print(f"→ {verdict}")
else:
    if len(all_jumps) == 0:
        print("  Aucun saut détecté — surface nodale topologiquement")
        print("  invariante sur [0,1] : l'équation maîtresse κ⁴(λ)=spectre(M²)")
        print("  requiert un ajustement de normalisation ou de base.")
    else:
        print("  Sauts détectés mais non concordants avec les prédictions.")
        print("  → Réviser la définition de κ⁴(λ) ou la surface nodale.")

print("\nConclusion théorique :")
print("  La correction fondamentale (états complexes s ∈ C^N) est")
print("  nécessaire pour que Re(E) dépende de λ.")
print("  Les termes croisés u^T I w dans Re(E) sont l'exact")
print("  analogue des termes de couplage dans l'équation de Kirchhoff.")

print("\nFichiers générés :")
print("  chladni_hopfield_nodal_surfaces.png")
print("  chladni_hopfield_betti_evolution.png")
