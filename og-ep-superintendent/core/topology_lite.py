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
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# PURE PYTHON SPARSE MATRIX (COO format)
# ─────────────────────────────────────────────────────────────────────────────

class SparseMatrix:
    """Minimal COO sparse matrix for field use."""
    def __init__(self, rows: list[int], cols: list[int], vals: list[float], shape: tuple[int, int]):
        self.rows = rows
        self.cols = cols
        self.vals = vals
        self.shape = shape

    def to_dense(self) -> list[list[float]]:
        n, m = self.shape
        M = [[0.0] * m for _ in range(n)]
        for r, c, v in zip(self.rows, self.cols, self.vals, strict=False):
            M[r][c] += v
        return M

    @classmethod
    def from_dense(cls, M: list[list[float]]) -> SparseMatrix:
        rows, cols, vals = [], [], []
        for i, row in enumerate(M):
            for j, v in enumerate(row):
                if abs(v) > 1e-12:
                    rows.append(i); cols.append(j); vals.append(v)
        return cls(rows, cols, vals, (len(M), len(M[0])))

    def matvec(self, x: list[float]) -> list[float]:
        n = self.shape[0]
        y = [0.0] * n
        for r, c, v in zip(self.rows, self.cols, self.vals, strict=False):
            y[r] += v * x[c]
        return y


def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b, strict=False))

def _norm(a: list[float]) -> float:
    return math.sqrt(sum(x*x for x in a))

def _normalize(a: list[float]) -> list[float]:
    n = _norm(a)
    if n < 1e-14:
        return a
    return [x / n for x in a]


def power_iteration_lambda1(L: SparseMatrix, k: int = 80, tol: float = 1e-6) -> float:
    """
    Approximate λ₁ (second smallest eigenvalue of Laplacian) via shift-invert
    without matrix inversion:

        1.  lam_max   = forward power iteration on L       (largest eigenvalue)
        2.  B.matvec  = lam_max·v − L·v                   (shifted operator)
        3.  lam_max_B = forward power iteration on B       (largest of B)
        4.  λ₁        = lam_max − lam_max_B                (second smallest of L)

    Forward power iteration on L converges to λ_MAX (largest eigenvalue).
    Applying the same to (lam_max·I − L) gives lam_max − λ₁ as its largest
    eigenvalue, so λ₁ = lam_max − result.  Axiom A6: correct answer > wrong answer.
    """
    n = L.shape[0]
    if n < 2:
        return 0.0

    def _power_max(matvec_fn, seed: int = 42) -> float:
        """Forward power iteration with nullspace deflation."""
        random.seed(seed)
        v = [random.gauss(0, 1) for _ in range(n)]
        mean_v = sum(v) / n
        v = _normalize([x - mean_v for x in v])
        lam = 0.0
        for _ in range(k):
            Lv = matvec_fn(v)
            mean_Lv = sum(Lv) / n
            Lv = [x - mean_Lv for x in Lv]          # deflate nullspace
            lam_new = _dot(v, Lv) / max(1e-14, _dot(v, v))
            v = _normalize(Lv)
            if abs(lam_new - lam) < tol:
                lam = lam_new
                break
            lam = lam_new
        return max(0.0, lam)

    # Step 1: largest eigenvalue of L
    lam_max = _power_max(L.matvec)
    if lam_max < 1e-10:
        return 0.0

    # Step 2-3: largest eigenvalue of (lam_max·I − L)
    def _shifted_matvec(v: list[float]) -> list[float]:
        Lv = L.matvec(v)
        return [lam_max * vi - Lvi for vi, Lvi in zip(v, Lv, strict=False)]

    lam_max_B = _power_max(_shifted_matvec, seed=137)

    # Step 4: λ₁ = lam_max − lam_max_B
    return max(0.0, lam_max - lam_max_B)


def count_connected_components(adj: dict[int, list[int]], n: int) -> int:
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


def build_laplacian(rows: list[int], cols: list[int], vals: list[float],
                    n: int) -> tuple[SparseMatrix, dict[int, list[int]]]:
    """Build L = DᵀD style Laplacian from edge list."""
    # Degree vector
    deg = [0.0] * n
    adj: dict[int, list[int]] = {i: [] for i in range(n)}

    for r, c, v in zip(rows, cols, vals, strict=False):
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
    for r, c, v in zip(rows, cols, vals, strict=False):
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
) -> dict[str, Any]:
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
