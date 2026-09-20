#!/usr/bin/env python3
"""Compare RMSNorm et LayerNorm sur leur sensibilité à deux types de
perturbation d'un état de base (cf. discussion du 2026-09-18,
docs/DevPlan.md) :

  - perturbation "DC" : décalage uniforme ε·(1,1,...,1) — exactement la
    direction que le centrage de LayerNorm annule par construction.
  - perturbation "orthogonale" : direction aléatoire de moyenne nulle
    (orthogonale à (1,...,1)), même norme ε.

Prédiction analytique à vérifier : LayerNorm doit être quasi insensible à
la perturbation DC (distance de sortie ≈0) tout en restant sensible à la
perturbation orthogonale ; RMSNorm doit rester sensible aux deux.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from src.hermitian.norm import HermitianLayerNorm, HermitianRMSNorm

torch.manual_seed(0)

D_MODEL = 8
EPSILON = 0.05

z0_real = torch.randn(1, D_MODEL)
z0_imag = torch.randn(1, D_MODEL)

u_dc = torch.ones(1, D_MODEL) / (D_MODEL**0.5)  # direction "décalage uniforme", norme 1

v = torch.randn(1, D_MODEL)
v = v - v.mean(dim=-1, keepdim=True)  # projette hors de la direction DC (moyenne nulle)
v = v / v.norm(dim=-1, keepdim=True)  # norme 1, comparable à u_dc

z_dc_real = z0_real + EPSILON * u_dc
z_orth_real = z0_real + EPSILON * v

rmsnorm = HermitianRMSNorm(D_MODEL, eps=1e-8)
layernorm = HermitianLayerNorm(D_MODEL, eps=1e-8)

def distance(norm_module, real_a, imag_a, real_b, imag_b):
    out_a_real, out_a_imag = norm_module(real_a, imag_a)
    out_b_real, out_b_imag = norm_module(real_b, imag_b)
    return torch.sqrt((out_a_real - out_b_real) ** 2 + (out_a_imag - out_b_imag) ** 2).sum().item()

d_dc_rms = distance(rmsnorm, z0_real, z0_imag, z_dc_real, z0_imag)
d_dc_ln = distance(layernorm, z0_real, z0_imag, z_dc_real, z0_imag)
d_orth_rms = distance(rmsnorm, z0_real, z0_imag, z_orth_real, z0_imag)
d_orth_ln = distance(layernorm, z0_real, z0_imag, z_orth_real, z0_imag)

print(f"{'perturbation':>14} | {'RMSNorm':>12} | {'LayerNorm':>12}")
print("-" * 44)
print(f"{'DC (ε·1)':>14} | {d_dc_rms:>12.6f} | {d_dc_ln:>12.6f}")
print(f"{'orthogonale':>14} | {d_orth_rms:>12.6f} | {d_orth_ln:>12.6f}")
