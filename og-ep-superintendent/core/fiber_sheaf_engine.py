"""
OG-EP SUPERINTENDENT SYSTEM
core/fiber_sheaf_engine.py

Fiber Bundle Sheaf Laplacian — Markov Chain Encoding —
Riemann Zeta Zero Spectral Embedding

════════════════════════════════════════════════════════════════════
MATHEMATICAL ARCHITECTURE
════════════════════════════════════════════════════════════════════

I.  FIBER BUNDLE OVER THE COST / WELLBORE GRAPH
────────────────────────────────────────────────
    Base space  B = G = (V, E)       cost-code or wellbore-interval graph
    Fiber       F_v ≅ ℝ^d            local d-dimensional state at each node v
    Total space E = ⊕_{v∈V} F_v      direct sum, dimension n·d
    Section     σ : V → E,  σ(v) ∈ F_v

    Restriction maps (connection 1-form on the bundle):
        ρ_{uv} : F_u → F_v   (d×d linear map per oriented edge)

        Built via Rodrigues parallel transport + coherence scaling:
            ρ_{uv} = c_{uv} · R(ŝ_u → ŝ_v)
        where c_{uv} ∈ [0,1] = agreement score
              R(ŝ_u → ŝ_v) ∈ SO(d) = rotation in plane(ŝ_u, ŝ_v)

        Key property: ρ_{uv}ᵀ ρ_{uv} = c_{uv}² · I_d

II.  SHEAF LAPLACIAN  L_F  (BLOCK MATRIX)
──────────────────────────────────────────
    L_F ∈ ℝ^{nd × nd}, assembled from d×d blocks:

        L_F[v,v] = Σ_{u∼v} ρ_{vu}ᵀ ρ_{vu}      diagonal block
        L_F[u,v] = −ρ_{uv}ᵀ ρ_{vu}              off-diagonal block

    L_F ⪰ 0 (positive semi-definite).
    ker(L_F) = space of global harmonic sections.
    dim ker(L_F) counts "agreement components" in the bundle —
      richer than the scalar dim H⁰.

    Spectral gap:  λ₁(L_F) measures coherence velocity in the bundle.
    λ₁(L_F) > 0  ↔  the bundle admits no non-trivial flat section
                      (no hidden contradictions).

    The off-diagonal blocks −ρ_{uv}ᵀ ρ_{vu} encode CURVATURE:
        when ρ_{uv}ᵀ ρ_{vu} ≠ I   →   non-trivial holonomy around loops.

III. MARKOV CHAIN ON THE TOTAL SPACE
──────────────────────────────────────
    Block transition matrix T ∈ ℝ^{nd × nd}:

        T[u→v]  = (1/Z_u) · ρ_{uv}
        Z_u     = Σ_{v∼u} ‖ρ_{uv}‖_F      fiber degree

    T is the fiber-bundle generalisation of the graph random walk.
    Stationary distribution:  π ∈ ℝ^{nd},   T π = π  (power iteration).

    Markov encoding of node v:
        m_v = π[v·d : (v+1)·d] ∈ ℝ^d   (long-run fiber weight)

    The fiber Markov chain is ergodic iff the bundle is connected and
    restriction maps are non-singular — equivalent to λ₁(L_F) > 0.

IV.  RIEMANN ZETA ZERO SPECTRAL FILTER
────────────────────────────────────────
    Non-trivial zeros of ζ(s) on critical line:  s_n = ½ + i·t_n
    First 30 values hard-coded as ZETA_ZEROS_T (LMFDB verified).

    Zeta-weighted matricised Laplacian  L_ζ:
        L_ζ = Σ_n w_n · cos(t_n · L_F)
            = V · diag(f_ζ(λ_k)) · Vᵀ
        where  f_ζ(λ) = Σ_n w_n · cos(t_n · λ)
               w_n    = exp(−t_n / τ)   decay weight

    Spectral zeta function of L_F:
        ζ_L(s) = Σ_{λ_k > 0} λ_k^{−s}
        evaluated at s = ½ + i·t_n for each zeta zero t_n.

    Zeta coherence:
        Z_coh = mean_n |ζ_L(½ + i·t_n)| / ζ_L(½)
        → 1 when spectrum resonates with prime frequencies (GUE / RMT)
        → 0 when spectrum is de-correlated (Poisson / fragmented)

V.   VON MANGOLDT PRIME SECTION WEIGHTING
──────────────────────────────────────────
    Each node v (index n_v ∈ ℕ) receives Von Mangoldt weight:
        Λ(n_v) = log p   if n_v = p^k for prime p
               = 0       otherwise

    Prime-encoded section:  s̃_v = (1 + Λ(n_v)) · s_v

    Up-weights nodes at topologically irreducible positions
    (primes in the index ordering encode structural primitives).

    Prime resonance of the spectrum:
        R_p = |Σ_k exp(i·2π·λ_k / log p)| / N    per prime p
        Averaged over first 10 primes → prime_resonance ∈ [0,1].

════════════════════════════════════════════════════════════════════
IP NOTICE  —  ZuluYokohama Protocol
════════════════════════════════════════════════════════════════════
    The combination of:
      • Fiber-bundle sheaf Laplacian for O&G operational coherence
      • Markov chain encoding of restriction maps on total space
      • Riemann zeta zero spectral filter as a coherence metric
      • Von Mangoldt prime weighting of operational state vectors
    applied to AFE budget topology and wellbore interval graphs
    constitutes a novel technical method.
    See FIBER_SHEAF_ZETA_BRAINSTORM.md for full IP/patent analysis.
════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

import numpy as np
from scipy.linalg import eigh as dense_eigh
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh

if TYPE_CHECKING:
    from .afe_laplacian import AFEState
    from .wellbore_topology import WellState

# ─────────────────────────────────────────────────────────────────────────────
# I.  GLOBAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

FIBER_DIM: int = 5      # Default ℝ^d fiber dimension
ZETA_DECAY: float = 50.0  # τ in w_n = exp(-t_n/τ)

# Non-trivial zeros of ζ(s) on critical line  Re(s) = ½
# s_n = ½ + i·t_n,  ζ(½ + i·t_n) = 0   (LMFDB / Odlyzko tables, 6dp)
ZETA_ZEROS_T: np.ndarray = np.array([
     14.134725,  21.022040,  25.010858,  30.424876,  32.935062,
     37.586178,  40.918720,  43.327073,  48.005151,  49.773832,
     52.970321,  56.446248,  59.347044,  60.831778,  65.112544,
     67.079811,  69.546402,  72.067158,  75.704691,  77.144840,
     79.337375,  82.910381,  84.735493,  87.425275,  88.809112,
     92.491899,  94.651344,  95.870634,  98.831194, 101.317851,
], dtype=np.float64)

ZETA_WEIGHTS: np.ndarray = np.exp(-ZETA_ZEROS_T / ZETA_DECAY)

# First 30 primes (for Von Mangoldt and prime resonance)
_PRIMES: List[int] = [
      2,   3,   5,   7,  11,  13,  17,  19,  23,  29,
     31,  37,  41,  43,  47,  53,  59,  61,  67,  71,
     73,  79,  83,  89,  97, 101, 103, 107, 109, 113,
]

# AFE cost-code dependency edges (duplicated here for standalone use)
_AFE_COST_DEPS: List[Tuple[str, str]] = [
    ("100", "200"), ("100", "230"), ("200", "210"),
    ("200", "220"), ("220", "230"), ("300", "320"),
    ("310", "300"), ("500", "100"),
]


# ─────────────────────────────────────────────────────────────────────────────
# II.  MATHEMATICAL PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────

def von_mangoldt(n: int) -> float:
    """
    Λ(n) = log(p)  if n = p^k for some prime p and k ≥ 1,  else 0.
    The Von Mangoldt function — encodes the prime skeleton of ℕ.

    Uses full trial division up to √n — correct for ALL n, not just
    those whose prime factors appear in the pre-computed _PRIMES table.
    """
    if n < 2:
        return 0.0
    p = 2
    while p * p <= n:
        if n % p == 0:
            # n is divisible by p.  Check if n = p^k exactly.
            k = n
            while k % p == 0:
                k //= p
            if k == 1:          # n = p^j  → Λ(n) = log p
                return math.log(p)
            else:               # n has at least two distinct prime factors
                return 0.0
        p += 1 if p == 2 else 2
    # No factor found up to √n  →  n is prime itself
    return math.log(n)


def rodrigues_rotation(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    R ∈ SO(d) that rotates  û  toward  v̂  in the plane they span.
    Generalised Rodrigues formula (works in any dimension d ≥ 2):

        S = (v̂ û^T − û v̂^T) / sin θ        (skew generator)
        R = I + sin θ · S + (1 − cos θ) · S²

    Properties:
        R û  =  v̂                   (maps first basis vector to second)
        R^T R = I                   (orthogonal)
        det R = +1                  (proper rotation, no reflection)
        θ = 0  →  R = I             (parallel sections → identity map)
        θ = π  →  R = -I            (anti-parallel → negation)
    """
    d = len(u)
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return np.eye(d, dtype=np.float64)

    u_hat = u / nu
    v_hat = v / nv
    cos_t_raw = float(np.dot(u_hat, v_hat))

    # Check parallel / anti-parallel BEFORE clipping (clipping hides the singularity)
    if cos_t_raw >= 1.0 - 1e-7:                    # parallel  → identity
        return np.eye(d, dtype=np.float64)
    if cos_t_raw <= -1.0 + 1e-7:                   # anti-parallel
        # -I ∈ SO(d) only when d is even; for odd d det(-I)=-1 (wrong sign).
        # Use a π-rotation in the plane(u_hat, e) where e ⊥ u_hat:
        #   R = I - 2·uu^T - 2·ee^T  →  det R = +1  for all d  ✓
        e = np.zeros(d, dtype=np.float64)
        e[int(np.argmin(np.abs(u_hat)))] = 1.0
        e -= np.dot(e, u_hat) * u_hat
        nrm = np.linalg.norm(e)
        if nrm < 1e-12:
            e = np.zeros(d, dtype=np.float64)
            e[(int(np.argmin(np.abs(u_hat))) + 1) % d] = 1.0
            e -= np.dot(e, u_hat) * u_hat
            nrm = np.linalg.norm(e)
        e /= max(nrm, 1e-12)
        return np.eye(d, dtype=np.float64) - 2.0 * np.outer(u_hat, u_hat) - 2.0 * np.outer(e, e)

    cos_t = cos_t_raw
    sin_t = math.sqrt(max(0.0, 1.0 - cos_t * cos_t))

    S  = (np.outer(v_hat, u_hat) - np.outer(u_hat, v_hat)) / sin_t
    S2 = S @ S
    return np.eye(d, dtype=np.float64) + sin_t * S + (1.0 - cos_t) * S2


def restriction_map(s_u: np.ndarray, s_v: np.ndarray, coherence: float) -> np.ndarray:
    """
    ρ_{uv} : F_u → F_v

        ρ_{uv} = c · R(ŝ_u → ŝ_v)

    where c = coherence ∈ [0,1]  and  R ∈ SO(d) is the Rodrigues rotation.

    ρ_{uv}^T ρ_{uv} = c² · I_d  (scaled identity — parallel transport).

    The curvature of the bundle appears in the off-diagonal sheaf blocks:
        L_F[u,v] = −ρ_{uv}^T ρ_{vu} = −c² · R_{u→v}^T · R_{v→u}
    which is non-trivial (≠ −c² I) whenever R_{u→v} R_{v→u} ≠ I,
    i.e., whenever the round-trip transport introduces a rotation —
    the holonomy of the connection.
    """
    R = rodrigues_rotation(s_u, s_v)
    return coherence * R


# ─────────────────────────────────────────────────────────────────────────────
# III.  FIBER BUNDLE DATA STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FiberBundle:
    """
    A vector bundle E → B over a finite graph G = (V, E).

    n           number of nodes  |V|
    d           fiber dimension  (each F_v ≅ ℝ^d)
    node_names  human-readable labels for V
    sections    (n, d) array — the local state vector at each node
    edges       list of (u, v, coherence) — directed edge list
    restriction_maps  dict (u,v) → d×d matrix ρ_{uv}
    """
    n: int
    d: int
    node_names: List[str]
    sections: np.ndarray                           # shape (n, d)
    edges: List[Tuple[int, int, float]]            # (u, v, c)
    restriction_maps: Dict[Tuple[int, int], np.ndarray]

    @classmethod
    def build(
        cls,
        node_names: List[str],
        raw_sections,              # list of array-like, possibly ragged
        edges: List[Tuple[int, int, float]],
        d: int = FIBER_DIM,
        prime_weight: bool = True,
    ) -> "FiberBundle":
        """
        Factory. Accepts ragged list of array-like sections — each entry
        is independently converted, padded, or truncated to d.
        Builds restriction maps for BOTH orientations of every edge so
        build_block_laplacian() never has to fall back to rho_uv.T.
        """
        n = len(node_names)
        # Pad or truncate each section to d independently (handles ragged input)
        secs = np.zeros((n, d), dtype=np.float64)
        for i, s in enumerate(raw_sections):
            s_arr = np.asarray(s, dtype=np.float64).ravel()
            l = min(len(s_arr), d)
            secs[i, :l] = s_arr[:l]

        # Von Mangoldt prime weighting on sections
        if prime_weight:
            for i in range(n):
                secs[i] *= (1.0 + von_mangoldt(i + 1))

        # Build restriction maps for BOTH orientations — no rho_uv.T fallback
        rho: Dict[Tuple[int, int], np.ndarray] = {}
        for (u, v, _c) in edges:
            if (u, v) not in rho:
                rho[(u, v)] = restriction_map(secs[u], secs[v], _c)
            if (v, u) not in rho:
                rho[(v, u)] = restriction_map(secs[v], secs[u], _c)

        return cls(
            n=n, d=d,
            node_names=node_names,
            sections=secs,
            edges=edges,
            restriction_maps=rho,
        )


# ─────────────────────────────────────────────────────────────────────────────
# IV.  SHEAF LAPLACIAN + MARKOV CHAIN OPS
# ─────────────────────────────────────────────────────────────────────────────

class FiberSheafOps:
    """
    Assembles L_F and computes its spectral invariants.
    Also builds the Markov chain on the total space E = ⊕ F_v.
    """

    def __init__(self, bundle: FiberBundle):
        self.b = bundle
        self._L:     Optional[np.ndarray] = None
        self._evals: Optional[np.ndarray] = None
        self._evecs: Optional[np.ndarray] = None

    # ── Sheaf Laplacian ──────────────────────────────────────────────────────

    def build_block_laplacian(self) -> np.ndarray:
        """
        Assemble L_F ∈ ℝ^{nd × nd}.

        Diagonal block  L_F[v,v] = Σ_{u∼v} ρ_{vu}ᵀ ρ_{vu}
        Off-diagonal    L_F[u,v] = −ρ_{uv}ᵀ ρ_{vu}
        """
        n, d = self.b.n, self.b.d
        nd = n * d
        L = np.zeros((nd, nd), dtype=np.float64)

        for (u, v, c) in self.b.edges:
            rho_uv = self.b.restriction_maps.get((u, v), np.zeros((d, d)))
            rho_vu = self.b.restriction_maps.get((v, u), rho_uv.T)

            # Diagonal accumulation
            L[u*d:(u+1)*d, u*d:(u+1)*d] += rho_uv.T @ rho_uv
            L[v*d:(v+1)*d, v*d:(v+1)*d] += rho_vu.T @ rho_vu

            # Off-diagonal blocks (curvature / holonomy lives here)
            L[u*d:(u+1)*d, v*d:(v+1)*d] -= rho_uv.T @ rho_vu
            L[v*d:(v+1)*d, u*d:(u+1)*d] -= rho_vu.T @ rho_uv

        # Symmetrise for numerical cleanliness
        self._L = (L + L.T) * 0.5
        return self._L

    def eigendecompose(self) -> Tuple[np.ndarray, np.ndarray]:
        """Full eigendecomposition.  Returns (eigenvalues asc, eigenvectors)."""
        if self._L is None:
            self.build_block_laplacian()
        evals, evecs = dense_eigh(self._L)
        idx = np.argsort(evals)
        self._evals = evals[idx]
        self._evecs = evecs[:, idx]
        return self._evals, self._evecs

    def lambda_1_fiber(self) -> float:
        """Spectral gap of L_F — smallest strictly positive eigenvalue."""
        if self._evals is None:
            self.eigendecompose()
        pos = self._evals[self._evals > 1e-10]
        return float(pos[0]) if len(pos) else 0.0

    def harmonic_dim(self) -> int:
        """
        dim ker(L_F) — number of global harmonic sections.
        Each harmonic section corresponds to one 'consistent assignment'
        of fibers across connected components.
        In the wellbore context: dim ker > 1 signals disconnected
        operational components that aren't talking to each other.
        """
        if self._evals is None:
            self.eigendecompose()
        thresh = 1e-8 * max(float(np.max(np.abs(self._evals))), 1.0)
        return int(np.sum(self._evals < thresh))

    def fiber_holonomy_trace(self) -> float:
        """
        Holonomy measure: tr(−L_F off-diagonal blocks) / n
        Quantifies total rotational drift accumulated around all loops.
        0.0  = flat connection (trivial holonomy, no contradiction)
        > 0  = non-trivial holonomy (restriction maps don't commute around cycles)
        """
        if self._L is None:
            self.build_block_laplacian()
        n, d = self.b.n, self.b.d
        offdiag_trace = 0.0
        for u in range(n):
            for v in range(u + 1, n):
                block = self._L[u*d:(u+1)*d, v*d:(v+1)*d]
                offdiag_trace += float(np.trace(block @ block.T))
        return offdiag_trace / max(n, 1)

    # ── Markov chain on total space ──────────────────────────────────────────

    def build_markov_transition(self) -> np.ndarray:
        """
        Block transition matrix T ∈ ℝ^{nd × nd}.

            T[u→v] = (1/Z_u) · ρ_{uv}
            Z_u    = Σ_{v∼u} ‖ρ_{uv}‖_F   (fiber degree)

        Generalises the row-normalised adjacency to fiber-bundle walks.
        The Markov chain on E = ⊕ F_v propagates fiber sections
        along restriction maps, weighted by coherence.
        """
        n, d = self.b.n, self.b.d
        nd = n * d
        T = np.zeros((nd, nd), dtype=np.float64)

        # Compute fiber degrees
        Z = np.zeros(n, dtype=np.float64)
        for (u, v, c) in self.b.edges:
            rho_uv = self.b.restriction_maps.get((u, v), np.zeros((d, d)))
            rho_vu = self.b.restriction_maps.get((v, u), rho_uv.T)
            Z[u] += np.linalg.norm(rho_uv, 'fro')
            Z[v] += np.linalg.norm(rho_vu, 'fro')

        # Fill transition blocks
        for (u, v, c) in self.b.edges:
            rho_uv = self.b.restriction_maps.get((u, v), np.zeros((d, d)))
            rho_vu = self.b.restriction_maps.get((v, u), rho_uv.T)
            z_u = max(Z[u], 1e-12)
            z_v = max(Z[v], 1e-12)
            T[u*d:(u+1)*d, v*d:(v+1)*d] += rho_uv / z_u
            T[v*d:(v+1)*d, u*d:(u+1)*d] += rho_vu / z_v

        return T

    def markov_stationary(self, max_iter: int = 300, tol: float = 1e-10) -> np.ndarray:
        """
        Stationary distribution of T via power iteration.
        π_{t+1} = T π_t  until ‖π_{t+1} − π_t‖₁ < tol.

        Returns π ∈ ℝ^{nd} — the long-run fiber weight vector.
        Interpretation: π_v = π[v·d:(v+1)·d] is the 'importance fiber'
        of node v under the Markov dynamics of the bundle.
        """
        T = self.build_markov_transition()
        nd = T.shape[0]
        pi = np.full(nd, 1.0 / nd, dtype=np.float64)
        for _ in range(max_iter):
            pi_new = T @ pi
            norm = np.linalg.norm(pi_new, 1)
            pi_new /= norm if norm > 1e-14 else 1.0
            if np.linalg.norm(pi_new - pi, 1) < tol:
                break
            pi = pi_new
        return pi_new

    def markov_diffusion_map(self, t: int = 3, k: int = 4) -> np.ndarray:
        """
        Diffusion map coordinates for nodes.
        Uses the top-k eigenvectors of T^t (T applied t times)
        scaled by eigenvalue^t → Φ_v ∈ ℝ^k per node.

        Provides a Markov-geometric embedding of each node
        that respects the fiber structure.
        """
        T = self.build_markov_transition()
        nd = T.shape[0]
        n, d = self.b.n, self.b.d

        # Symmetrise T for stable eigendecomposition (detailed balance approx)
        Ts = (T + T.T) * 0.5
        evals_t, evecs_t = dense_eigh(Ts)
        idx = np.argsort(-np.abs(evals_t))       # descending by magnitude
        evals_t = evals_t[idx]
        evecs_t = evecs_t[:, idx]

        k_use = min(k, nd - 1)
        # Diffusion coordinates: scale eigenvectors by λ^t
        diffusion = evecs_t[:, :k_use] * (np.abs(evals_t[:k_use]) ** t)

        # Aggregate per node: mean of fiber slice in diffusion space
        node_coords = np.zeros((n, k_use), dtype=np.float64)
        for v in range(n):
            node_coords[v] = diffusion[v*d:(v+1)*d].mean(axis=0)

        return node_coords   # (n, k_use)

    def node_markov_weights(self) -> np.ndarray:
        """Per-node importance from stationary distribution (L2 norm of fiber slice)."""
        pi = self.markov_stationary()
        n, d = self.b.n, self.b.d
        w = np.array([float(np.linalg.norm(pi[v*d:(v+1)*d])) for v in range(n)])
        w /= w.sum() + 1e-14
        return w


# ─────────────────────────────────────────────────────────────────────────────
# V.   RIEMANN ZETA ZERO SPECTRAL EMBEDDER
# ─────────────────────────────────────────────────────────────────────────────

class ZetaSpectralEmbedder:
    """
    Applies the Riemann zeta zeros as a spectral filter over L_F.

    Three core products:
      1. zeta_matricized(L)        →  L_ζ  ∈ ℝ^{nd × nd}
      2. spectral_zeta_function(λ) →  ζ_L(½ + i·t_n) ∈ ℂ^N
      3. zeta_coherence(λ)         →  Z_coh ∈ [0,∞)
      4. zeta_embedding(λ)         →  ℝ^{2N} embedding vector
      5. prime_resonance(λ)        →  scalar ∈ [0,1]

    The connection to the Riemann Hypothesis:
        If ζ_L behaves like ζ_Riemann (GUE eigenvalue spacing),
        then Z_coh → 1 and prime_resonance is maximised.
        This corresponds to a "quantum chaotic" system — all operational
        components maximally coupled, no information hidden.
        Deviations signal structured (predictable) failure modes.
    """

    zeros   = ZETA_ZEROS_T
    weights = ZETA_WEIGHTS

    # ── Matricised operator ──────────────────────────────────────────────────

    @classmethod
    def zeta_matricized(cls, L: np.ndarray) -> np.ndarray:
        """
        L_ζ = Σ_n w_n · cos(t_n · L_F)
            = V · diag(f_ζ(λ_k)) · Vᵀ

        where  f_ζ(λ) = Σ_n w_n cos(t_n λ)   (zeta-cosine filter on spectrum)

        L_ζ is a smooth function of L_F in the spectral calculus sense.
        Negative eigenvalues of L_ζ signal anti-resonance with prime frequencies.
        The ratio  λ₁(L_ζ) / λ₁(L_F)  measures how 'prime-structured'
        the coherence loss is.
        """
        evals, evecs = dense_eigh(L)
        f_zeta = np.zeros(len(evals), dtype=np.float64)
        for t, w in zip(cls.zeros, cls.weights):
            f_zeta += w * np.cos(t * evals)
        return (evecs * f_zeta) @ evecs.T   # V diag(f) Vᵀ

    # ── Spectral zeta function ────────────────────────────────────────────────

    @classmethod
    def spectral_zeta_function(cls, evals: np.ndarray) -> np.ndarray:
        """
        ζ_L(½ + i·t_n) = Σ_{λ_k > 0} λ_k^{−½} · exp(−i·t_n · ln λ_k)

        This is the graph's analogue of the Riemann zeta function,
        evaluated at the non-trivial zeros of ζ_Riemann.
        Returns complex array of length len(ZETA_ZEROS_T).

        Interpretation:
          Large |ζ_L(½ + i·t_n)| → the Laplacian spectrum 'resonates'
          at zeta-zero frequency t_n → that frequency band is active in
          the operational graph.
        """
        pos = evals[evals > 1e-10]
        if len(pos) == 0:
            return np.zeros(len(cls.zeros), dtype=complex)

        log_pos       = np.log(pos)            # (m,)
        inv_sqrt_pos  = pos ** (-0.5)          # (m,)

        # ζ_L(½ + i·t_n) = Σ_k λ_k^{-½} e^{-i t_n ln λ_k}
        # Vectorised over all t_n at once: (N, m) @ (m,) → (N,)
        phase = np.exp(-1j * np.outer(cls.zeros, log_pos))   # (N, m)
        return phase @ inv_sqrt_pos                           # (N,)

    # ── Coherence metrics ─────────────────────────────────────────────────────

    @classmethod
    def zeta_coherence(cls, evals: np.ndarray) -> float:
        """
        Z_coh = mean_n |ζ_L(½ + i·t_n)| / ζ_L(½)

        Normalised by  ζ_L(½) = Σ λ_k^{−½}  (the real baseline).

        Z_coh ≈ 1  →  spectrum has GUE / prime-resonant statistics.
        Z_coh → 0  →  spectrum is Poisson (compartmentalised, fragmented).
        """
        zv   = cls.spectral_zeta_function(evals)
        pos  = evals[evals > 1e-10]
        if len(pos) == 0:
            return 0.0
        zeta_half = float(np.sum(pos ** (-0.5)))
        if zeta_half < 1e-12:
            return 0.0
        return float(np.mean(np.abs(zv))) / zeta_half

    @classmethod
    def zeta_embedding_vector(cls, evals: np.ndarray) -> np.ndarray:
        """
        ℝ^{2N} zeta embedding of the Laplacian spectrum.
        Concatenation of normalised real + imaginary parts of ζ_L at each zero.
        Scale-invariant (normalised by ζ_L(½)).
        """
        zv   = cls.spectral_zeta_function(evals)
        pos  = evals[evals > 1e-10]
        norm = float(np.sum(pos ** (-0.5))) if len(pos) > 0 else 1.0
        norm = max(norm, 1e-12)
        return np.concatenate([np.real(zv) / norm, np.imag(zv) / norm])

    @classmethod
    def prime_resonance(cls, evals: np.ndarray) -> float:
        """
        For each prime p in first 10 primes:
            R_p = |Σ_k exp(i · 2π · λ_k / log p)| / N

        prime_resonance = mean_{p} R_p

        High → eigenvalues cluster at multiples of prime log-frequencies
               (the spectrum 'counts' primes → quantum chaos signature).
        Low  → eigenvalues are random / uniform
               (fragmented structure → operational silos).
        """
        pos = evals[evals > 1e-10]
        if len(pos) == 0:
            return 0.0
        scores = []
        for p in _PRIMES[:10]:
            freq = 2.0 * math.pi / math.log(p)
            r = float(np.abs(np.sum(np.exp(1j * freq * pos)))) / len(pos)
            scores.append(r)
        return float(np.mean(scores))

    @classmethod
    def lambda1_zeta_laplacian(cls, L_zeta: np.ndarray) -> float:
        """λ₁ of L_ζ — spectral gap of the zeta-matricised operator."""
        evals_z, _ = dense_eigh(L_zeta)
        pos_z = evals_z[evals_z > 1e-10]
        return float(pos_z[0]) if len(pos_z) else 0.0

    @classmethod
    def zeta_gate(cls, evals: np.ndarray) -> str:
        """
        Gate decision based on zeta coherence + prime resonance.
        PASS → coherent, prime-resonant spectrum (RMT / GUE-like).
        WARN → partial coherence.
        HALT_A4 → spectrum collapsed / Poisson fragmented.
        """
        zc = cls.zeta_coherence(evals)
        pr = cls.prime_resonance(evals)
        score = 0.6 * zc + 0.4 * pr
        if score > 0.3:
            return "PASS"
        elif score > 0.1:
            return "WARN"
        else:
            return "HALT_A4"


# ─────────────────────────────────────────────────────────────────────────────
# VI.  FIBER SHEAF ENGINE  —  top-level integration
# ─────────────────────────────────────────────────────────────────────────────

class FiberSheafEngine:
    """
    Top-level engine.  Builds the fiber bundle from AFE or wellbore data,
    runs the three-layer analysis, returns an enriched K(S) dict.

    Usage:
        # From AFEState:
        engine = FiberSheafEngine.from_afe(afe_state)
        ks = engine.compute()

        # From WellState:
        engine = FiberSheafEngine.from_well(well_state)
        ks = engine.compute()

        # From raw sections + edge list:
        engine = FiberSheafEngine.from_raw(node_names, sections, edges)
        ks = engine.compute()

    Output dict keys:
        fiber_dim, n_nodes, node_names
        lambda_1_fiber         spectral gap of L_F
        harmonic_dim           dim ker(L_F)
        fiber_holonomy_trace   curvature measure
        markov_node_weights    per-node Markov importance
        markov_top_node        most important node under Markov dynamics
        diffusion_coords       (n, 4) diffusion map coordinates
        zeta_coherence         Z_coh
        lambda_1_zeta          λ₁ of L_ζ
        prime_resonance        prime-frequency resonance
        zeta_embedding         ℝ^{2N} spectral fingerprint
        zeta_gate              PASS / WARN / HALT_A4
        ks_fiber_score         composite score ∈ [0,1]
    """

    def __init__(self, bundle: FiberBundle):
        self.bundle    = bundle
        self.sheaf_ops = FiberSheafOps(bundle)
        self.zeta      = ZetaSpectralEmbedder

    # ── Factory: from raw data ────────────────────────────────────────────────

    @classmethod
    def from_raw(
        cls,
        node_names: List[str],
        raw_sections,              # list of array-like, may be ragged
        edges: List[Tuple[int, int, float]],
        fiber_dim: int = FIBER_DIM,
        prime_weight: bool = True,
    ) -> "FiberSheafEngine":
        """Build engine from node sections + edge list. Sections may be ragged."""
        bundle = FiberBundle.build(
            node_names=node_names,
            raw_sections=raw_sections,   # passed as-is; build() handles ragged
            edges=edges,
            d=fiber_dim,
            prime_weight=prime_weight,
        )
        return cls(bundle)

    # ── Factory: from AFEState ────────────────────────────────────────────────

    @classmethod
    def from_afe(
        cls,
        afe_state: "AFEState",
        fiber_dim: int = FIBER_DIM,
        prime_weight: bool = True,
    ) -> "FiberSheafEngine":
        """
        Build fiber bundle from an AFE budget state.

        Fiber at cost-code node v ∈ ℝ^d:
            [approved_norm, actual_norm, forecast_norm, coherence, under_budget]
        Edges from COST_DEPENDENCIES; coherence = geometric mean of both nodes.
        """
        items = afe_state.line_items
        n     = len(items)
        max_usd = max((li.afe_approved_usd for li in items), default=1.0) or 1.0

        node_names   = [f"{li.cost_code}:{li.description[:18]}" for li in items]
        raw_sections = []
        for li in items:
            s = np.array([
                li.afe_approved_usd        / max_usd,
                li.actual_to_date_usd      / max_usd,
                li.forecast_to_complete_usd / max_usd,
                li.coherence_score,
                max(0.0, -li.variance_pct),       # under-budget component
            ], dtype=np.float64)
            raw_sections.append(s)

        code_to_idx = {li.cost_code: i for i, li in enumerate(items)}
        edges: List[Tuple[int, int, float]] = []
        for (ca, cb) in _AFE_COST_DEPS:
            if ca in code_to_idx and cb in code_to_idx:
                u, v = code_to_idx[ca], code_to_idx[cb]
                # coherence_score is a @property on AFELineItem
                c = (items[u].coherence_score * items[v].coherence_score) ** 0.5
                edges.append((u, v, c))   # undirected; build() creates (v,u) map

        bundle = FiberBundle.build(
            node_names=node_names,
            raw_sections=np.array(raw_sections),
            edges=edges,
            d=fiber_dim,
            prime_weight=prime_weight,
        )
        return cls(bundle)

    # ── Factory: from WellState ───────────────────────────────────────────────

    @classmethod
    def from_well(
        cls,
        well_state: "WellState",
        fiber_dim: int = FIBER_DIM,
        prime_weight: bool = True,
    ) -> "FiberSheafEngine":
        """
        Build fiber bundle from a wellbore state.

        Fiber at interval node v ∈ ℝ^d:
            [depth_norm, rop_norm, mw_norm, ecd_norm, npt_norm]
        Synthetic nodes: AFE_DRILLING, CONTRACTOR_DIRECTIONAL,
                         CONTRACTOR_MUD, CONTRACTOR_MUDLOG
        """
        ivs   = well_state.intervals
        n_iv  = len(ivs)
        td    = well_state.td_planned_ft or 1.0
        cost_eff = well_state.cost_efficiency

        node_names = [iv.interval_id for iv in ivs]
        node_names += ["AFE_DRILLING", "CONTRACTOR_DIRECTIONAL",
                       "CONTRACTOR_MUD", "CONTRACTOR_MUDLOG"]
        n = len(node_names)

        active = next((iv for iv in ivs if iv.is_active), ivs[-1])
        ecd_delta = abs(well_state.ecd_ppg - active.mud_weight_ppg)
        rop_norm  = min(1.0, active.rop_fthr / 100.0)

        raw_sections: List[np.ndarray] = []
        for iv in ivs:
            raw_sections.append(np.array([
                iv.bottom_depth_ft / td,
                min(1.0, iv.rop_fthr / 100.0),
                iv.mud_weight_ppg  / 20.0,
                (well_state.ecd_ppg if iv.is_active else iv.mud_weight_ppg) / 20.0,
                min(1.0, iv.npt_hours / 24.0),
            ], dtype=np.float64))

        # Synthetic node sections
        raw_sections.append(np.array([cost_eff, well_state.afe_burn_rate,
                                       0.5, 0.5, 0.0], dtype=np.float64))   # AFE
        raw_sections.append(np.array([rop_norm, min(1.0, well_state.wob_klbs / 30.0),
                                       0.7, 0.0, 0.0], dtype=np.float64))   # DIR
        raw_sections.append(np.array([max(0.0, 1.0 - ecd_delta * 2.0),
                                       active.mud_weight_ppg / 20.0,
                                       0.7, 0.0, 0.0], dtype=np.float64))   # MUD
        raw_sections.append(np.array([0.9, 0.9, 0.7, 0.0, 0.0],
                                       dtype=np.float64))                     # MLOG

        # Edges
        afe_idx  = node_names.index("AFE_DRILLING")
        dir_idx  = node_names.index("CONTRACTOR_DIRECTIONAL")
        mud_idx  = node_names.index("CONTRACTOR_MUD")
        mlog_idx = node_names.index("CONTRACTOR_MUDLOG")
        act_idx  = next((i for i, iv in enumerate(ivs) if iv.is_active), 0)

        edges: List[Tuple[int, int, float]] = []
        # Interval chain
        for i in range(n_iv - 1):
            agr = 1.0 if ivs[i].is_cased else 0.5
            edges.append((i, i + 1, agr))   # undirected; build() creates reverse

        # Active interval → synthetic nodes
        afe_agr  = max(0.0, 1.0 - abs(1.0 - cost_eff))
        mud_agr  = max(0.0, 1.0 - ecd_delta * 2.0)
        dir_agr  = rop_norm if well_state.wob_klbs > 0 else 0.3
        mlog_agr = 0.9 if active.is_active else 0.5

        for (idx, agr) in [(afe_idx, afe_agr), (dir_idx, dir_agr),
                           (mud_idx, mud_agr), (mlog_idx, mlog_agr)]:
            edges.append((act_idx, idx, agr))   # undirected; build() creates reverse

        bundle = FiberBundle.build(
            node_names=node_names,
            raw_sections=np.array(raw_sections, dtype=np.float64),
            edges=edges,
            d=fiber_dim,
            prime_weight=prime_weight,
        )
        return cls(bundle)

    # ── Main compute ──────────────────────────────────────────────────────────

    def compute(self) -> Dict[str, Any]:
        """
        Full three-layer enriched K(S) computation.

        Layer 1 — Fiber sheaf Laplacian:
            λ₁(L_F), dim ker(L_F), fiber holonomy trace

        Layer 2 — Markov chain on total space:
            stationary node weights, diffusion map coordinates

        Layer 3 — Zeta zero spectral embedding:
            ζ_L at Riemann zeros, Z_coh, prime resonance,
            L_ζ spectral gap, zeta gate

        Composite score:
            ks_fiber_score = tanh(λ₁ · 10)·0.4 + Z_coh·0.35 + R_prime·0.25
        """
        # ── Layer 1: Sheaf Laplacian ──────────────────────────────────────
        L_F          = self.sheaf_ops.build_block_laplacian()
        evals, evecs = self.sheaf_ops.eigendecompose()
        lam1_f       = self.sheaf_ops.lambda_1_fiber()
        h_dim        = self.sheaf_ops.harmonic_dim()
        hol_trace    = self.sheaf_ops.fiber_holonomy_trace()

        # ── Layer 2: Markov chain ─────────────────────────────────────────
        markov_w     = self.sheaf_ops.node_markov_weights()
        top_node     = self.bundle.node_names[int(np.argmax(markov_w))]
        diffusion    = self.sheaf_ops.markov_diffusion_map(t=3, k=4)

        # ── Layer 3: Zeta spectral embedding ──────────────────────────────
        L_zeta       = self.zeta.zeta_matricized(L_F)
        zeta_coh     = self.zeta.zeta_coherence(evals)
        lam1_zeta    = self.zeta.lambda1_zeta_laplacian(L_zeta)
        prime_res    = self.zeta.prime_resonance(evals)
        zeta_emb     = self.zeta.zeta_embedding_vector(evals)
        z_gate       = self.zeta.zeta_gate(evals)

        # ── Composite score ───────────────────────────────────────────────
        ks_score = (
            math.tanh(lam1_f * 10) * 0.40 +
            min(1.0, zeta_coh)     * 0.35 +
            prime_res              * 0.25
        )

        # ── Gate (combine fiber + zeta signals) ───────────────────────────
        if lam1_f < 1e-6 or z_gate == "HALT_A4":
            gate = "HALT_A4"
        elif lam1_f < 1e-3 or z_gate == "WARN":
            gate = "WARN"
        else:
            gate = "PASS"

        return {
            # Identity
            "fiber_dim":              self.bundle.d,
            "n_nodes":                self.bundle.n,
            "node_names":             self.bundle.node_names,

            # Layer 1 — Sheaf Laplacian
            "lambda_1_fiber":         round(lam1_f, 8),
            "harmonic_dim":           h_dim,
            "fiber_holonomy_trace":   round(hol_trace, 6),
            "eigenvalues_top8":       [round(float(e), 6) for e in evals[:8]],

            # Layer 2 — Markov chain
            "markov_node_weights":    [round(float(w), 6) for w in markov_w],
            "markov_top_node":        top_node,
            "diffusion_coords":       [[round(float(x), 6) for x in row]
                                       for row in diffusion],

            # Layer 3 — Zeta spectral
            "zeta_coherence":         round(zeta_coh, 6),
            "lambda_1_zeta":          round(lam1_zeta, 6),
            "prime_resonance":        round(prime_res, 6),
            "zeta_embedding_dim":     len(zeta_emb),
            "zeta_embedding":         [round(float(x), 6) for x in zeta_emb],
            "zeta_gate":              z_gate,

            # Composite
            "ks_fiber_score":         round(ks_score, 6),
            "gate":                   gate,
        }


# ─────────────────────────────────────────────────────────────────────────────
# VII.  DELTA K(S) — enriched Δ between two states
# ─────────────────────────────────────────────────────────────────────────────

def compute_delta_fiber(
    prior_ks:   Dict[str, Any],
    current_ks: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute the enriched delta between two fiber K(S) snapshots.

    Returns Δλ₁_fiber, Δzeta_coherence, Δprime_resonance,
    a composite Δscore, and a gate decision.
    """
    d_lam1  = current_ks["lambda_1_fiber"]   - prior_ks["lambda_1_fiber"]
    d_zcoh  = current_ks["zeta_coherence"]   - prior_ks["zeta_coherence"]
    d_pres  = current_ks["prime_resonance"]  - prior_ks["prime_resonance"]
    d_score = current_ks["ks_fiber_score"]   - prior_ks["ks_fiber_score"]

    if d_lam1 < -0.5 or d_score < -0.3:
        gate = "HALT_A4"
    elif d_lam1 < -0.1 or d_score < -0.1:
        gate = "WARN"
    else:
        gate = "PASS"

    return {
        "delta_lambda_1_fiber":  round(d_lam1, 8),
        "delta_zeta_coherence":  round(d_zcoh, 6),
        "delta_prime_resonance": round(d_pres, 6),
        "delta_ks_fiber_score":  round(d_score, 6),
        "gate":                  gate,
        "a4_triggered":          gate == "HALT_A4",
    }
