import pytest
import torch

# Tolérances fixées a priori (falsifiabilité avant calcul, cf. CLAUDE.md) —
# arithmétique flottante FP32 sur des opérations simples (matmul, softmax,
# eigh) : 1e-5 absolu / 1e-4 relatif est large par rapport au bruit
# d'arrondi attendu (~1e-7), donc un dépassement signale un vrai bug, pas
# du bruit numérique.
ATOL = 1e-5
RTOL = 1e-4


@pytest.fixture(autouse=True)
def _fixed_seed():
    torch.manual_seed(0)
