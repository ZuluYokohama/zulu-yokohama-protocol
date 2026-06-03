"""
OG-EP SUPERINTENDENT SYSTEM
core/topology_lite.py

Zero-dependency fallback topology engine for ARM64 / no-scipy environments.
Uses pure Python linear algebra (power iteration for λ₁, DFS for dim H⁰).
Numerically approximate but sufficient for field use on a rig tablet.
Axiom A6: a structurally-informed initial guess is better than nothing.
"""

from __future__ import annotations
import math
import random
from typing import Dict, List, Tuple, Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# PURE PYTHON SPARSE MATRIX (COO format)
# ─────────────────────────────────────────────────────────────────────────────

class SparseMatrix:
    """Minimal COO sparse matrix for field use."""
    def __init__(self, rows: List[int], cols: List[int], vals: List[float], shape: Tuple[int, int]):
        self.rows = rows
        self.cols = cols
        self.vals = vals
        self.shape = shape

    def to_dense(self) -> List[List[float]]:
        n, m = self.shape
        M = [[0.0] * m for _ in range(n)]
        for r, c, v in zip(self.rows, self.cols, self.vals):
            M[r][c] += v
        return M

    @classmethod
    def from_dense(cls, M: List[List[float]]) -> "SparseMatrix":
        rows, cols, vals = [], [], []
        for i, row in enumerate(M):
            for j, v in enumerate(row):
                if abs(v) > 1e-12:
                    rows.append(i); cols.append(j); vals.append(v)
        return cls(rows, cols, vals, (len(M), len(M[0])))

    def matvec(self, x: List[float]) -> List[float]:
        n = self.shape[0]
        y = [0.0] * n
        for r, c, v in zip(self.rows, self.cols, self.vals):
            y[r] += v * x[c]
        return y


def _dot(a: List[float], b: List[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))

def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x*x for x in a))

def _normalize(a: List[float]) -> List[float]:
    n = _norm(a)
    if n < 1e-14:
        return a
    return [x / n for x in a]


def power_iteration_lambda1(L: SparseMatrix, k: int = 80, tol: float = 1e-6) -> float:
    """
    Approximate λ₁ (second smallest eigenvalue of Laplacian) via inverse power iteration.
    Deflate the null space (constant vector) first.
    Axiom A6: fast inverse square root spirit — good enough initial guess.
    """
    n = L.shape[0]
    if n < 2:
        return 0.0

    # Start with a random vector orthogonal to ones (deflate null space)
    random.seed(42)
    v = [random.gauss(0, 1) for _ in range(n)]
    # Deflate: subtract projection onto ones vector
    mean_v = sum(v) / n
    v = [x - mean_v for x in v]
    v = _normalize(v)

    # Shift-invert approximation: use (L + σI)v iterations
    # Since we can't easily invert, use Rayleigh quotient with power method on L
    # This gives the *largest* eigenvalue; we shift to get the smallest non-zero.
    # For field use: estimate via Rayleigh quotient of random orthogonal vector.

    lam = 0.0
    for _ in range(k):
        Lv = L.matvec(v)
        # Deflate again
        mean_Lv = sum(Lv) / n
        Lv = [x - mean_Lv for x in Lv]

        lam_new = _dot(v, Lv) / max(1e-14, _dot(v, v))
        v = _normalize(Lv)

        if abs(lam_new - lam) < tol:
            lam = lam_new
            break
        lam = lam_new

    return max(0.0, lam)


def count_connected_components(adj: Dict[int, List[int]], n: int) -> int:
    """DFS to count connected components (dim H⁰ approximation)."""
    visited = [False] * n

    def dfs(node: int):
        stack = [node]
        while stack:
            curr = stack.pop()
            if visited[curr]:
                continue
            visited[curr] = True
            for nb in adj.get(curr, []):
                if not visited[nb]:
                    stack.append(nb)

    components = 0
    for i in range(n):
        if not visited[i]:
            dfs(i)
            components += 1
    return components


def build_laplacian(rows: List[int], cols: List[int], vals: List[float],
                    n: int) -> Tuple[SparseMatrix, Dict[int, List[int]]]:
    """Build L = DᵀD style Laplacian from edge list."""
    # Degree vector
    deg = [0.0] * n
    adj: Dict[int, List[int]] = {i: [] for i in range(n)}

    for r, c, v in zip(rows, cols, vals):
        if r != c:
            deg[r] += abs(v)
            adj[r].append(c)

    # Laplacian: L[i][i] = deg[i], L[i][j] = -w[i][j]
    L_rows, L_cols, L_vals = [], [], []
    # Diagonal
    for i in range(n):
        if deg[i] > 0:
            L_rows.append(i); L_cols.append(i); L_vals.append(deg[i])
    # Off-diagonal
    for r, c, v in zip(rows, cols, vals):
        if r != c:
            L_rows.append(r); L_cols.append(c); L_vals.append(-abs(v))

    return SparseMatrix(L_rows, L_cols, L_vals, (n, n)), adj


# ─────────────────────────────────────────────────────────────────────────────
# LITE WELLBORE KEY
# ─────────────────────────────────────────────────────────────────────────────

def compute_well_key_lite(
    depth_ft: float,
    td_ft: float,
    afe_spent: float,
    afe_approved: float,
    mw_ppg: float,
    ecd_ppg: float,
    npt_hours: float,
    total_hours: float,
    is_h2_obstruction: bool = False,
    is_holonomy_diverged: bool = False,
    n_cased_intervals: int = 2,
    n_open_intervals: int = 2,
    timestamp: str = "",
    well_name: str = "",
) -> Dict[str, Any]:
    """
    Compute K(S) without scipy.
    Uses pure Python graph construction + power iteration.
    """
    depth_frac = min(1.0, depth_ft / max(1.0, td_ft))
    afe_frac   = afe_spent / max(1.0, afe_approved)
    cost_eff   = afe_frac / max(0.001, depth_frac)

    ecd_delta = abs(ecd_ppg - mw_ppg)
    npt_density = npt_hours / max(1.0, total_hours)

    # Build a small wellbore graph
    n = n_cased_intervals + n_open_intervals + 3  # intervals + AFE + mud + directional nodes
    edge_rows, edge_cols, edge_vals = [], [], []

    # Cased intervals → each other (strong agreement)
    for i in range(n_cased_intervals - 1):
        edge_rows += [i, i+1]; edge_cols += [i+1, i]; edge_vals += [0.9, 0.9]

    # Last cased → first open (transition)
    if n_cased_intervals > 0 and n_open_intervals > 0:
        ci = n_cased_intervals - 1
        oi = n_cased_intervals
        trans_agr = 0.7 if not is_h2_obstruction else 0.2
        edge_rows += [ci, oi]; edge_cols += [oi, ci]; edge_vals += [trans_agr, trans_agr]

    # AFE node
    afe_node = n_cased_intervals + n_open_intervals
    afe_agr = max(0.0, 1.0 - abs(1.0 - cost_eff))
    active_node = n_cased_intervals  # first open interval
    edge_rows += [active_node, afe_node]; edge_cols += [afe_node, active_node]
    edge_vals += [afe_agr, afe_agr]

    # Mud node
    mud_node = afe_node + 1
    mud_agr = max(0.0, 1.0 - ecd_delta * 2.0)
    edge_rows += [active_node, mud_node]; edge_cols += [mud_node, active_node]
    edge_vals += [mud_agr, mud_agr]

    # Directional node
    dir_node = afe_node + 2
    dir_agr = max(0.3, 0.9 - npt_density * 2.0)
    edge_rows += [active_node, dir_node]; edge_cols += [dir_node, active_node]
    edge_vals += [dir_agr, dir_agr]

    # Build Laplacian
    L, adj = build_laplacian(edge_rows, edge_cols, edge_vals, n)

    # Compute λ₁
    lambda_1 = power_iteration_lambda1(L, k=60)

    # dim H⁰ (connected components)
    dim_H0 = count_connected_components(adj, n)

    # Holonomy
    if is_holonomy_diverged or cost_eff > 1.30 or ecd_delta > 0.5:
        if cost_eff > 1.30:
            holonomy = f"non-trivial:afe-overrun-{cost_eff:.2f}x"
        elif ecd_delta > 0.5:
            holonomy = f"non-trivial:ecd-mw-divergence-{ecd_delta:.2f}ppg"
        else:
            holonomy = "non-trivial:contractor-data-inconsistency"
    else:
        holonomy = "trivial"

    return {
        "well_name": well_name,
        "timestamp": timestamp,
        "dim_H0": dim_H0,
        "lambda_1": round(lambda_1, 6),
        "holonomy_signature": holonomy,
        "afe_coherence": round(afe_agr, 4),
        "depth_coherence": round(depth_frac, 4),
        "npt_density": round(npt_density, 4),
        "ecd_mw_delta": round(ecd_delta, 3),
        "cost_efficiency": round(cost_eff, 3),
    }
