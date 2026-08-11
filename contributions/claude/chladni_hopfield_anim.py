"""
Visualisation animée — Isomorphisme Chladni–Hopfield complexe
=============================================================
Bertrand Gervais — Géométrie de la Cognition (§7)

Trois couches superposées, animées en fonction de λ :

  1. Heatmap de Re(E(s))
     Fond coloré : rouge = énergie positive, bleu = énergie négative.
     Les lignes nodales Re(E)=0 sont les frontières blanc/noir.
     Pics (maxima) et creux (minima) marqués par ▲ et ▼.

  2. Mouvement des lignes nodales
     Les courbes Re(E_i)=0 et Re(E_j)=0 se déplacent et pivotent
     avec λ. Le saut topologique (tangence) est signalé en rouge.

  3. Trajectoire s(t) sous V_ext
     Le réseau part d'un état initial s0, évolue sous la dynamique
       ds/dt = -∇Re(E) + Γ · V_ext
     La trajectoire est tracée en blanc avec un point mobile.

Contrôles :
  - Slider λ : navigation manuelle dans [0, 1.6]
  - Bouton Play/Pause : animation automatique
  - Bouton Export : sauvegarde chaque frame en PNG

Usage :
  python chladni_hopfield_anim.py

Dépendances :
  pip install numpy scipy matplotlib
"""

import numpy as np
import matplotlib
matplotlib.use("TkAgg")          # GUI interactive — remplacer par Qt5Agg si nécessaire
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
from scipy.ndimage import label, gaussian_filter
from scipy.signal import argrelmin, argrelmax
import warnings
warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
# 1. Construction de M(λ) = R + λC + iλD
# ═══════════════════════════════════════════════════════════════
N = 8

patterns = np.array([
    [+1, +1, -1, -1, +1, +1, -1, -1],
    [+1, -1, +1, -1, +1, -1, +1, -1],
    [+1, -1, -1, +1, +1, -1, +1, -1],
    [+1, -1, +1, -1, +1, -1, +1, -1],
    [+1, -1, -1, +1, +1, -1, +1, -1],
    [+1, -1, +1, -1, +1, -1, +1, -1],
    [+1, -1, +1, -1, +1, -1, +1, -1],
    [+1, -1, -1, +1, +1, -1, +1, -1]
], dtype=float)
np.random.seed(42)
R = np.zeros((N, N))
for p in patterns:
    R += np.outer(p, p)
R /= N
np.fill_diagonal(R, 0)

np.random.seed(13)
A = np.random.randn(N, N);  C_mat = 0.3 * (A + A.T) / 2
B = np.random.randn(N, N);  D_mat = 0.5 * (B + B.T) / 2

# Vecteur d'excitation externe V_ext (input cognitif / musical)
# Modifiable : représente le stimulus appliqué au réseau
np.random.seed(7)
V_ext = np.random.randn(N)
V_ext /= np.linalg.norm(V_ext)

# Tenseur de friction Γ (scalaire pour simplifier)
Gamma = 0.4

# ═══════════════════════════════════════════════════════════════
# 2. Suivi des valeurs/vecteurs propres de M(λ)
# ═══════════════════════════════════════════════════════════════
N_LAMBDA = 320
lambda_vals = np.linspace(0.0, 1.6, N_LAMBDA)

def track_eigenvalues(lambda_vals):
    n = len(lambda_vals)
    tv  = np.zeros((n, N), dtype=complex)
    tvc = np.zeros((n, N, N), dtype=complex)
    M0  = R + lambda_vals[0]*C_mat + 1j*lambda_vals[0]*D_mat
    ev, evc = np.linalg.eig(M0)
    order = np.argsort(np.real(ev))
    tv[0]  = ev[order]
    tvc[0] = evc[:, order]
    for k in range(1, n):
        M_eff = R + lambda_vals[k]*C_mat + 1j*lambda_vals[k]*D_mat
        ev, evc = np.linalg.eig(M_eff)
        prev = tv[k-1].copy()
        assigned = [False]*N
        nv = [None]*N; nc = [None]*N
        for i in range(N):
            dists = [abs(ev[j]-prev[i]) if not assigned[j] else np.inf
                     for j in range(N)]
            best = int(np.argmin(dists))
            nv[i] = ev[best]; nc[i] = evc[:, best]; assigned[best] = True
        tv[k]  = nv
        tvc[k] = np.array(nc).T
    return tv, tvc

print("Calcul des trajectoires de valeurs propres...")
tracks_val, tracks_vec = track_eigenvalues(lambda_vals)

# Paire de modes qui se croisent (Re(μi) = Re(μj))
pair_i, pair_j = 0, 1

# λ_c topologiques (discriminant de tangence = 0)
def natural_basis(lam_idx):
    ei = tracks_vec[lam_idx, :, pair_i]
    ej = tracks_vec[lam_idx, :, pair_j]
    cols = np.column_stack([ei.real, ei.imag, ej.real, ej.imag])
    U, _, _ = np.linalg.svd(cols, full_matrices=False)
    return U[:, 0], U[:, 1]

def tangency_disc(lam_idx, b1, b2):
    def Qmat(k):
        mu = tracks_val[lam_idx, k]
        ek = tracks_vec[lam_idx, :, k]
        al = ek.conj() @ b1; be = ek.conj() @ b2
        q11 = np.real(-0.5*mu*al**2)
        q12 = np.real(-0.5*mu*al*be)
        q22 = np.real(-0.5*mu*be**2)
        return np.array([[q11, q12],[q12, q22]])
    Qi = Qmat(pair_i); Qj = Qmat(pair_j)
    a = np.linalg.det(Qj)
    adj = np.array([[Qj[1,1],-Qj[0,1]],[-Qj[1,0],Qj[0,0]]])
    b = np.trace(adj @ Qi)
    c = np.linalg.det(Qi)
    return b**2 - 4*a*c

discs = []
for k in range(N_LAMBDA):
    b1, b2 = natural_basis(k)
    discs.append(tangency_disc(k, b1, b2))
discs = np.array(discs)

lambda_c_topo = []
for k in range(1, len(discs)):
    if np.sign(discs[k]) != np.sign(discs[k-1]):
        lc = lambda_vals[k-1] - discs[k-1]*(lambda_vals[k]-lambda_vals[k-1])/(discs[k]-discs[k-1])
        lambda_c_topo.append(float(lc))

print(f"  λ_c topologiques : {[round(l,4) for l in lambda_c_topo]}")

# ═══════════════════════════════════════════════════════════════
# 3. Grille d'états et calcul vectorisé de Re(E)
# ═══════════════════════════════════════════════════════════════
GRID_N  = 120
T_RANGE = 2.8
t_ax    = np.linspace(-T_RANGE, T_RANGE, GRID_N)
T1, T2  = np.meshgrid(t_ax, t_ax)

def compute_frame(lam_idx):
    """
    Calcule pour un λ donné :
      - E_total : Re(E) total = somme pondérée des modes
      - E_i, E_j : Re(E) des deux modes de la paire
      - attracteurs et répulseurs (min/max locaux)
      - trajectoire s(t) sous V_ext
    """
    b1, b2 = natural_basis(lam_idx)

    # Re(E) total = somme sur tous les modes
    E_total = np.zeros((GRID_N, GRID_N))
    for k in range(N):
        mu = tracks_val[lam_idx, k]
        ek = tracks_vec[lam_idx, :, k]
        al = ek.conj() @ b1
        be = ek.conj() @ b2
        proj = T1*al + T2*be
        E_total += np.real(-0.5 * mu * proj**2)

    # Re(E) individuel pour les deux modes de la paire
    def E_mode(k):
        mu = tracks_val[lam_idx, k]
        ek = tracks_vec[lam_idx, :, k]
        al = ek.conj() @ b1; be = ek.conj() @ b2
        proj = T1*al + T2*be
        return np.real(-0.5 * mu * proj**2)

    E_i = E_mode(pair_i)
    E_j = E_mode(pair_j)

    # Lissage pour détecter les extrema locaux
    E_smooth = gaussian_filter(E_total, sigma=3)

    # Attracteurs = minima locaux, répulseurs = maxima locaux
    from scipy.ndimage import minimum_filter, maximum_filter
    local_min = (E_smooth == minimum_filter(E_smooth, size=12))
    local_max = (E_smooth == maximum_filter(E_smooth, size=12))
    # Filtre par profondeur/hauteur relative
    threshold = 0.05 * (E_smooth.max() - E_smooth.min())
    attractors = np.argwhere(local_min & (E_smooth < E_smooth.mean() - threshold))
    repulsors  = np.argwhere(local_max & (E_smooth > E_smooth.mean() + threshold))

    # Trajectoire s(t) sous V_ext
    # ds/dt = -∇Re(E) + Γ·V_ext_proj
    # V_ext projeté dans le plan (b1, b2)
    vext_1 = V_ext @ b1
    vext_2 = V_ext @ b2

    dt = 0.05; n_steps = 80
    # État initial : léger déplacement depuis le centre
    traj = np.zeros((n_steps, 2))
    traj[0] = [0.3, 0.2]

    for step in range(1, n_steps):
        t1_c, t2_c = traj[step-1]
        # Gradient numérique de Re(E_total) au point courant
        dt_grad = 0.05
        E_c  = _e_total_point(lam_idx, b1, b2, t1_c, t2_c)
        E_p1 = _e_total_point(lam_idx, b1, b2, t1_c+dt_grad, t2_c)
        E_p2 = _e_total_point(lam_idx, b1, b2, t1_c, t2_c+dt_grad)
        grad1 = (E_p1 - E_c) / dt_grad
        grad2 = (E_p2 - E_c) / dt_grad
        # Dynamique : descente de gradient + poussée de V_ext
        # λ contrôle l'intensité de V_ext (plus λ grand = plus perturbé)
        lam = lambda_vals[lam_idx]
        dt1 = -grad1 + Gamma * lam * vext_1
        dt2 = -grad2 + Gamma * lam * vext_2
        t1_new = t1_c + dt * dt1
        t2_new = t2_c + dt * dt2
        # Clamp dans la fenêtre
        t1_new = np.clip(t1_new, -T_RANGE+0.1, T_RANGE-0.1)
        t2_new = np.clip(t2_new, -T_RANGE+0.1, T_RANGE-0.1)
        traj[step] = [t1_new, t2_new]

    return E_total, E_i, E_j, E_smooth, attractors, repulsors, traj

def _e_total_point(lam_idx, b1, b2, t1, t2):
    """Re(E_total) en un point scalaire."""
    E = 0.0
    for k in range(N):
        mu = tracks_val[lam_idx, k]
        ek = tracks_vec[lam_idx, :, k]
        proj = (ek.conj() @ b1)*t1 + (ek.conj() @ b2)*t2
        E += np.real(-0.5 * mu * proj**2)
    return E

# Pré-calcul des frames (sous-ensemble pour fluidité)
N_FRAMES = 60
frame_lambda_idx = np.linspace(0, N_LAMBDA-1, N_FRAMES, dtype=int)

print("Pré-calcul des frames...")
frames_data = []
for fi, lam_idx in enumerate(frame_lambda_idx):
    if fi % 10 == 0:
        print(f"  frame {fi}/{N_FRAMES}  λ={lambda_vals[lam_idx]:.3f}")
    frames_data.append(compute_frame(lam_idx))
print("  Pré-calcul terminé.")

# ═══════════════════════════════════════════════════════════════
# 4. Construction de la figure interactive
# ═══════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 9))
fig.patch.set_facecolor('#0d0d1a')

# Layout : visualisation principale + panneau latéral
gs = fig.add_gridspec(3, 3,
                      left=0.06, right=0.96,
                      top=0.92, bottom=0.14,
                      hspace=0.35, wspace=0.35)

ax_main  = fig.add_subplot(gs[:, :2])   # grande carte principale
ax_disc  = fig.add_subplot(gs[0, 2])    # discriminant de tangence vs λ
ax_re_ev = fig.add_subplot(gs[1, 2])    # Re(μk) vs λ
ax_traj  = fig.add_subplot(gs[2, 2])    # énergie le long de la trajectoire

for ax in [ax_main, ax_disc, ax_re_ev, ax_traj]:
    ax.set_facecolor('#0d0d1a')
    ax.tick_params(colors='#aaaacc', labelsize=7)
    for sp in ax.spines.values():
        sp.set_edgecolor('#333355')

# ── Panneau latéral haut : discriminant ──────────────────────
ax_disc.plot(lambda_vals, discs, color='#cc4444', lw=1.5,
             label='Discriminant tangence')
ax_disc.axhline(0, color='white', lw=0.8, ls=':')
for lc in lambda_c_topo:
    ax_disc.axvline(lc, color='#ff6666', ls='--', lw=1.2)
ax_disc.set_title("Discriminant det(Qi+tQj)", color='#aaaacc', fontsize=8)
ax_disc.set_xlabel("λ", color='#aaaacc', fontsize=7)
ax_disc.set_xlim(0, 1.6)
ax_disc.grid(alpha=0.2, color='#333355')
lambda_line_disc = ax_disc.axvline(lambda_vals[0], color='yellow', lw=1.5)

# ── Panneau latéral milieu : trajectoires Re(μk) ─────────────
colors_vp = ['#4488ff', '#ff8844', '#44cc88', '#cc44cc']
for k in range(N):
    ax_re_ev.plot(lambda_vals, np.real(tracks_val[:,k]),
                  color=colors_vp[k], lw=1.2, label=f'μ{k+1}')
for lc in lambda_c_topo:
    ax_re_ev.axvline(lc, color='#ff6666', ls='--', lw=1.0)
ax_re_ev.set_title("Re(μk) — valeurs propres", color='#aaaacc', fontsize=8)
ax_re_ev.set_xlabel("λ", color='#aaaacc', fontsize=7)
ax_re_ev.legend(fontsize=6, loc='upper left',
                facecolor='#0d0d1a', edgecolor='#333355',
                labelcolor='#aaaacc')
ax_re_ev.set_xlim(0, 1.6)
ax_re_ev.grid(alpha=0.2, color='#333355')
lambda_line_ev = ax_re_ev.axvline(lambda_vals[0], color='yellow', lw=1.5)

# ── Initialisation de la carte principale ────────────────────
E_total, E_i, E_j, E_smooth, attractors, repulsors, traj = frames_data[0]

vmax = np.percentile(np.abs(E_total), 96)
im = ax_main.imshow(E_total, origin='lower',
                    extent=[-T_RANGE, T_RANGE, -T_RANGE, T_RANGE],
                    cmap='RdBu_r', vmin=-vmax, vmax=vmax, alpha=0.85,
                    aspect='auto')

# Lignes nodales
cont_total = ax_main.contour(t_ax, t_ax, E_total, levels=[0.0],
                              colors='white', linewidths=1.5, alpha=0.9)
cont_i = ax_main.contour(t_ax, t_ax, E_i, levels=[0.0],
                          colors='#88ccff', linewidths=1.2,
                          linestyles='--', alpha=0.7)
cont_j = ax_main.contour(t_ax, t_ax, E_j, levels=[0.0],
                          colors='#ffcc88', linewidths=1.2,
                          linestyles=':', alpha=0.7)

# Attracteurs et répulseurs
scat_att = ax_main.scatter([], [], marker='v', s=120,
                            color='#00ffaa', zorder=5, label='Attracteurs')
scat_rep = ax_main.scatter([], [], marker='^', s=120,
                            color='#ff4444', zorder=5, label='Répulseurs')

# Trajectoire s(t)
traj_line, = ax_main.plot([], [], color='white', lw=1.5,
                           alpha=0.85, zorder=6)
traj_point, = ax_main.plot([], [], 'o', color='yellow',
                            ms=8, zorder=7)
traj_start, = ax_main.plot([], [], 's', color='#88ff88',
                             ms=7, zorder=7)

ax_main.set_xlim(-T_RANGE, T_RANGE)
ax_main.set_ylim(-T_RANGE, T_RANGE)
ax_main.set_xlabel("t₁  (amplitude — espace des modes)", color='#aaaacc', fontsize=9)
ax_main.set_ylabel("t₂  (phase — partie imaginaire)", color='#aaaacc', fontsize=9)

title_main = ax_main.set_title(
    f"Re(E) — Réseau Hopfield complexe    λ = {lambda_vals[0]:.3f}",
    color='white', fontsize=11, fontweight='bold'
)

# Légende
from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0],[0], color='white',    lw=1.5, label='Re(E_tot) = 0'),
    Line2D([0],[0], color='#88ccff',  lw=1.2, ls='--', label=f'Re(E_{pair_i+1}) = 0'),
    Line2D([0],[0], color='#ffcc88',  lw=1.2, ls=':', label=f'Re(E_{pair_j+1}) = 0'),
    Line2D([0],[0], marker='v', color='#00ffaa', ms=7, ls='', label='Attracteurs'),
    Line2D([0],[0], marker='^', color='#ff4444', ms=7, ls='', label='Répulseurs'),
    Line2D([0],[0], color='white',    lw=1.5, alpha=0.85, label='Trajectoire s(t)'),
    Line2D([0],[0], marker='o', color='yellow', ms=7, ls='', label='Position courante'),
]
ax_main.legend(handles=legend_handles, loc='upper right', fontsize=7,
               facecolor='#0d0d1a', edgecolor='#333355', labelcolor='#aaaacc')

# Colorbar
cbar = fig.colorbar(im, ax=ax_main, fraction=0.025, pad=0.01)
cbar.ax.tick_params(colors='#aaaacc', labelsize=7)
cbar.set_label("Re(E)", color='#aaaacc', fontsize=8)

# ── Panneau latéral bas : énergie le long de la trajectoire ──
ax_traj.set_title("Re(E) le long de s(t)", color='#aaaacc', fontsize=8)
ax_traj.set_xlabel("pas de temps", color='#aaaacc', fontsize=7)
ax_traj.set_ylabel("Re(E)", color='#aaaacc', fontsize=7)
ax_traj.grid(alpha=0.2, color='#333355')
ax_traj.axhline(0, color='white', lw=0.8, ls=':')
traj_energy_line, = ax_traj.plot([], [], color='#ffffaa', lw=1.5)

# Annotation critique
critical_text = ax_main.text(
    0.02, 0.03, "", transform=ax_main.transAxes,
    color='#ff6666', fontsize=9, fontweight='bold',
    bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a0000', alpha=0.8)
)

# ═══════════════════════════════════════════════════════════════
# 5. Fonction de mise à jour des frames
# ═══════════════════════════════════════════════════════════════
def get_frame_idx(lam_val):
    """Trouve l'index frame le plus proche d'une valeur λ."""
    lam_idx = np.argmin(np.abs(lambda_vals - lam_val))
    frame_distances = np.abs(frame_lambda_idx - lam_idx)
    return int(np.argmin(frame_distances))

def update_display(frame_idx):
    """Met à jour tous les éléments graphiques pour un frame donné."""
    global cont_total, cont_i, cont_j

    lam_idx = frame_lambda_idx[frame_idx]
    lam     = lambda_vals[lam_idx]
    E_total, E_i, E_j, E_smooth, attractors, repulsors, traj = frames_data[frame_idx]

    # Heatmap
    vmax = np.percentile(np.abs(E_total), 96) + 1e-6
    im.set_data(E_total)
    im.set_clim(-vmax, vmax)

    # Retracer les contours (nécessite de les supprimer et recréer)
    def _remove_contour(cs):
        if hasattr(cs, 'collections'):
            for coll in cs.collections:
                coll.remove()
        elif hasattr(cs, 'remove'):
            cs.remove()

    _remove_contour(cont_total)
    _remove_contour(cont_i)
    _remove_contour(cont_j)

    cont_total = ax_main.contour(t_ax, t_ax, E_total, levels=[0.0],
                                  colors='white', linewidths=1.5, alpha=0.9)
    cont_i = ax_main.contour(t_ax, t_ax, E_i, levels=[0.0],
                              colors='#88ccff', linewidths=1.2,
                              linestyles='--', alpha=0.7)
    cont_j = ax_main.contour(t_ax, t_ax, E_j, levels=[0.0],
                              colors='#ffcc88', linewidths=1.2,
                              linestyles=':', alpha=0.7)

    # Attracteurs / répulseurs
    if len(attractors) > 0:
        att_t1 = t_ax[attractors[:,1]]
        att_t2 = t_ax[attractors[:,0]]
        scat_att.set_offsets(np.c_[att_t1, att_t2])
    else:
        scat_att.set_offsets(np.empty((0,2)))

    if len(repulsors) > 0:
        rep_t1 = t_ax[repulsors[:,1]]
        rep_t2 = t_ax[repulsors[:,0]]
        scat_rep.set_offsets(np.c_[rep_t1, rep_t2])
    else:
        scat_rep.set_offsets(np.empty((0,2)))

    # Trajectoire
    traj_line.set_data(traj[:,0], traj[:,1])
    traj_point.set_data([traj[-1,0]], [traj[-1,1]])
    traj_start.set_data([traj[0,0]], [traj[0,1]])

    # Énergie le long de la trajectoire
    traj_energies = [_e_total_point(lam_idx, *natural_basis(lam_idx), t[0], t[1])
                     for t in traj]
    traj_energy_line.set_data(range(len(traj_energies)), traj_energies)
    ax_traj.relim(); ax_traj.autoscale_view()

    # Indicateurs λ
    lambda_line_disc.set_xdata([lam, lam])
    lambda_line_ev.set_xdata([lam, lam])

    # Titre et annotation critique
    near_c = any(abs(lam - lc) < 0.05 for lc in lambda_c_topo)
    title_main.set_text(
        f"Re(E) — Réseau Hopfield complexe    λ = {lam:.3f}"
        + ("   ◀ SAUT TOPOLOGIQUE ▶" if near_c else "")
    )
    title_main.set_color('#ff6666' if near_c else 'white')

    if near_c:
        lc_near = min(lambda_c_topo, key=lambda l: abs(l-lam))
        critical_text.set_text(f"λ_c = {lc_near:.4f}\nTangence des coniques nodales")
    else:
        critical_text.set_text("")

    fig.canvas.draw_idle()

# Affichage initial
update_display(0)

# ═══════════════════════════════════════════════════════════════
# 6. Widgets : slider + boutons
# ═══════════════════════════════════════════════════════════════
ax_slider = fig.add_axes([0.08, 0.05, 0.60, 0.025])
ax_slider.set_facecolor('#1a1a2e')
slider = Slider(ax_slider, 'λ', 0.0, 1.6,
                valinit=lambda_vals[0], color='#4466aa')
slider.label.set_color('#aaaacc')
slider.valtext.set_color('#aaaacc')

ax_btn_play   = fig.add_axes([0.72, 0.045, 0.07, 0.04])
ax_btn_export = fig.add_axes([0.81, 0.045, 0.07, 0.04])

btn_play   = Button(ax_btn_play,   'Play ▶',
                    color='#1a1a3a', hovercolor='#2a2a5a')
btn_export = Button(ax_btn_export, 'Export',
                    color='#1a1a3a', hovercolor='#2a2a5a')
btn_play.label.set_color('#aaaacc')
btn_export.label.set_color('#aaaacc')

# État de l'animation
state = {'playing': False, 'frame': 0}
anim_obj = [None]

def on_slider(val):
    state['playing'] = False
    btn_play.label.set_text('Play ▶')
    lam = slider.val
    fi = get_frame_idx(lam)
    state['frame'] = fi
    update_display(fi)

slider.on_changed(on_slider)

def animate_step(frame_num):
    if not state['playing']:
        return
    fi = (state['frame'] + 1) % N_FRAMES
    state['frame'] = fi
    lam = lambda_vals[frame_lambda_idx[fi]]
    slider.set_val(lam)   # déclenche on_slider via callback

def on_play(event):
    state['playing'] = not state['playing']
    btn_play.label.set_text('Pause ⏸' if state['playing'] else 'Play ▶')
    if state['playing']:
        anim_obj[0] = animation.FuncAnimation(
            fig, animate_step, interval=80, cache_frame_data=False)
    else:
        if anim_obj[0]:
            anim_obj[0].event_source.stop()

def on_export(event):
    import os
    out_dir = "chladni_frames"
    os.makedirs(out_dir, exist_ok=True)
    print(f"Export des {N_FRAMES} frames vers ./{out_dir}/...")
    for fi in range(N_FRAMES):
        update_display(fi)
        lam = lambda_vals[frame_lambda_idx[fi]]
        fig.savefig(f"{out_dir}/frame_{fi:03d}_lambda{lam:.3f}.png",
                    dpi=100, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        if fi % 10 == 0:
            print(f"  {fi}/{N_FRAMES}")
    print(f"  Export terminé → {out_dir}/")

btn_play.on_clicked(on_play)
btn_export.on_clicked(on_export)

# ═══════════════════════════════════════════════════════════════
# 7. Lancement
# ═══════════════════════════════════════════════════════════════
fig.suptitle(
    "Isomorphisme Chladni–Hopfield  —  Dynamique des surfaces nodales et trajectoire cognitive",
    color='#ccccee', fontsize=11, fontweight='bold', y=0.97
)

print("\nFenêtre interactive ouverte.")
print("  Slider λ  : déplace la topologie")
print("  Play ▶    : animation automatique")
print("  Export    : sauvegarde toutes les frames en PNG")
print()

plt.show()
