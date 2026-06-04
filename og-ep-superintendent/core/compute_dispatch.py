"""
OG-EP SUPERINTENDENT SYSTEM
core/compute_dispatch.py

Compute Dispatch & Translation Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BENCHMARK BASELINE  (Termux / ARM64, numpy 2.4.4 / scipy 1.17.1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operation                     n=5    n=10   n=17   n=30   n=50
─────────────────────────────────────────────────────────────────
rodrigues_rotation  d=5      0.11ms
restriction_map     d=5      0.12ms
von_mangoldt(1..100)         0.20ms
─────────────────────────────────────────────────────────────────
build_bundle        d=5      1.7ms   3.0ms   5.2ms   9.4ms
build_L_F           d=5      0.9ms   1.7ms   2.9ms   5.4ms
─────────────────────────────────────────────────────────────────
dense_eigh          d=5      0.5ms   1.1ms   2.7ms   8.8ms  23.9ms
─────────────────────────────────────────────────────────────────
build_T   (Markov)  d=5      0.9ms   1.8ms   3.0ms   5.7ms
stationary (300-it) d=5     16.3ms  17.8ms  19.7ms  23.2ms   ← DOMINANT COST
─────────────────────────────────────────────────────────────────
spectral_zeta_fn    d=5      0.06ms  0.09ms  0.12ms  0.23ms  ← CHEAPEST
zeta_coherence      d=5      0.12ms  0.15ms  0.18ms  0.30ms
zeta_matricized     d=5      0.9ms   1.6ms   3.3ms   9.7ms
─────────────────────────────────────────────────────────────────
compute() FULL      d=5     26.1ms  32.1ms  46.2ms  83.4ms
─────────────────────────────────────────────────────────────────

KEY FINDINGS:
  • Markov stationary dominates (16–23ms, iteration-bound, near-flat in n)
  • zeta_fn / zeta_coherence are negligible (<0.3ms) — always include
  • zeta_matricized scales O((nd)³) — defer to FULL path only
  • dense_eigh bottleneck hits at n=30+ — switch to eigsh (sparse) above
  • Bundle construction is O(n) — cheap, always build fresh per DDR
  • AFE graph (n=17): 46ms full — fine for end-of-day DDR
  • Wellbore graph (n=10): 32ms full — fine for shift handoff
  • Real-time A4 alarm: use FAST path (<2ms) then FULL async

THREE DISPATCH TIERS:
  FAST     < 2ms   primitives + λ₁ only  (real-time alarm, mid-op)
  STANDARD < 15ms  sheaf + eigh + zeta_fn (shift handoff, hourly)
  FULL     < 90ms  everything incl. Markov + zeta_mat (DDR, daily)

TRANSLATION TABLE (math → operational action):
  λ₁_fiber ≥ 0.5   → COHERENT     advance, no action
  0.01 ≤ λ₁ < 0.5  → CAUTION      monitor, log to DDR
  0.001 ≤ λ₁ < 0.01 → WARN        wiper trip / mud check
  λ₁ < 0.001       → HALT_A4      stop operations

  zeta_coherence ≥ 0.4  → GUE / well-coupled system
  0.15 ≤ Z < 0.4        → partial coupling, isolated pockets
  Z < 0.15              → Poisson / siloed — no cross-node learning

  prime_resonance ≥ 0.5 → spectrum prime-resonant (robust)
  0.2 ≤ R < 0.5         → partial resonance
  R < 0.2               → de-resonated (fragmented structure)

  fiber_holonomy > 5.0  → non-trivial connection (loop contradiction)
  harmonic_dim > d      → disconnected bundle (information silo)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import time
import math
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Tuple, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .wellbore_topology import WellState
    from .afe_laplacian import AFEState

from .fiber_sheaf_engine import (
    FiberSheafEngine, FiberSheafOps, ZetaSpectralEmbedder,
    FiberBundle, compute_delta_fiber, FIBER_DIM,
    GATE_HALT_LAMBDA, GATE_WARN_LAMBDA,   # shared threshold constants
)


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TIER ENUM
# ─────────────────────────────────────────────────────────────────────────────

class Tier(str, Enum):
    FAST     = "FAST"       # < 2ms   — real-time A4 gate, mid-operation
    STANDARD = "STANDARD"   # < 15ms  — shift handoff, hourly snapshot
    FULL     = "FULL"       # < 90ms  — end-of-day DDR, batch analysis


# ─────────────────────────────────────────────────────────────────────────────
# OPERATION COST TABLE  (ms, from ARM64 benchmark)
# ─────────────────────────────────────────────────────────────────────────────

# Coefficients fitted from benchmark: cost = a * n + b  (ms)
_COST: Dict[str, Dict[str, float]] = {
    "bundle_build":     {"a": 0.313, "b": 0.22},   # per node
    "laplacian_build":  {"a": 0.154, "b": 0.10},
    "eigendecompose":   {"a": 0.278, "b": 0.06},   # n·d ≤ 150 region
    "markov_build":     {"a": 0.162, "b": 0.07},
    "markov_stationary":{"a": 0.235, "b": 15.6},   # flat ~16-23ms
    "zeta_fn":          {"a": 0.006, "b": 0.05},   # near-zero
    "zeta_coherence":   {"a": 0.006, "b": 0.11},
    "zeta_matricized":  {"a": 0.300, "b": 0.30},   # O((nd)^1.5) approx
    "diffusion_map":    {"a": 0.250, "b": 0.10},
}

def _estimate_ms(op: str, n: int) -> float:
    c = _COST.get(op, {"a": 0.1, "b": 0.1})
    return c["a"] * n + c["b"]

def _tier_budget(tier: Tier) -> float:
    return {"FAST": 2.0, "STANDARD": 15.0, "FULL": 90.0}[tier]


# ─────────────────────────────────────────────────────────────────────────────
# OPERATION PLAN  — which steps run at each tier
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OpPlan:
    tier:              Tier
    n_nodes:           int
    fiber_dim:         int
    run_bundle:        bool = True
    run_laplacian:     bool = True
    run_eigendecompose:bool = True
    run_zeta_fn:       bool = True     # always cheap, always include
    run_zeta_coherence:bool = True
    run_zeta_mat:      bool = False    # expensive, FULL only
    run_markov_T:      bool = False
    run_markov_stat:   bool = False    # dominant cost, FULL only
    run_diffusion:     bool = False
    estimated_ms:      float = 0.0

    @classmethod
    def for_tier(cls, tier: Tier, n: int, d: int) -> "OpPlan":
        plan = cls(tier=tier, n_nodes=n, fiber_dim=d)
        est = 0.0
        est += _estimate_ms("bundle_build", n)
        est += _estimate_ms("laplacian_build", n)
        est += _estimate_ms("eigendecompose", n * d)
        est += _estimate_ms("zeta_fn", n * d)
        est += _estimate_ms("zeta_coherence", n * d)

        if tier == Tier.FAST:
            plan.run_zeta_fn      = True
            plan.run_zeta_coherence = True
            plan.run_zeta_mat     = False
            plan.run_markov_T     = False
            plan.run_markov_stat  = False
            plan.run_diffusion    = False

        elif tier == Tier.STANDARD:
            plan.run_zeta_fn      = True
            plan.run_zeta_coherence = True
            plan.run_zeta_mat     = False
            plan.run_markov_T     = True
            plan.run_markov_stat  = False   # skip power iteration
            plan.run_diffusion    = False
            est += _estimate_ms("markov_build", n)

        else:  # FULL
            plan.run_zeta_fn      = True
            plan.run_zeta_coherence = True
            plan.run_zeta_mat     = True
            plan.run_markov_T     = True
            plan.run_markov_stat  = True
            plan.run_diffusion    = True
            est += _estimate_ms("markov_build", n)
            est += _estimate_ms("markov_stationary", n)
            est += _estimate_ms("zeta_matricized", n * d)
            est += _estimate_ms("diffusion_map", n * d)

        plan.estimated_ms = round(est, 2)
        return plan


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATION TABLE  — math output → operational language
# ─────────────────────────────────────────────────────────────────────────────

def _translate_lambda1(v: float) -> Dict[str, str]:
    if v >= 0.5:
        return {"level": "COHERENT",  "colour": "GREEN",
                "action": "System coherent. Advance operations per program."}
    elif v >= 0.01:
        return {"level": "CAUTION",   "colour": "YELLOW",
                "action": "Coherence degrading. Monitor next DDR. Log to superintendent."}
    elif v >= 0.001:
        return {"level": "WARN",      "colour": "ORANGE",
                "action": "Low spectral gap. Run wiper trip / mud check before next casing point."}
    else:
        return {"level": "HALT_A4",   "colour": "RED",
                "action": "A4 TRIGGERED. Halt operations. File corrective action. Do not advance."}

def _translate_zeta_coherence(z: float) -> Dict[str, str]:
    if z >= 0.4:
        return {"regime": "GUE",     "note": "Spectrum prime-resonant (well-coupled). Full cross-node learning active."}
    elif z >= 0.15:
        return {"regime": "MIXED",   "note": "Partial coupling. Some nodes isolated. Check MARKOV_TOP_NODE for bottleneck."}
    else:
        return {"regime": "POISSON", "note": "Fragmented (Poisson) spectrum. Components siloed. No coherence propagation."}

def _translate_prime_resonance(r: float) -> str:
    if r >= 0.5:
        return "Prime-resonant: system structure robust, eigenvalue spacing GUE-like."
    elif r >= 0.2:
        return "Partial prime resonance: mixed structure."
    else:
        return "De-resonated: fragmented eigenvalue distribution. Structural primitives disconnected."

def _translate_holonomy(trace: float, harmonic_dim: int, fiber_dim: int) -> Dict[str, str]:
    silo = harmonic_dim > fiber_dim
    if trace > 5.0 and silo:
        return {"status": "NON_TRIVIAL",
                "note": f"High holonomy ({trace:.2f}) + {harmonic_dim} harmonic sections "
                        f"(>{fiber_dim}). Multiple disconnected silos with loop contradictions. "
                        "Contractor reports likely inconsistent."}
    elif trace > 5.0:
        return {"status": "CURVED",
                "note": f"Holonomy trace {trace:.2f}. Restriction maps don't commute around loops. "
                        "Depth / formation readings may disagree between contractors."}
    elif silo:
        return {"status": "SILO",
                "note": f"{harmonic_dim} harmonic sections (fiber_dim={fiber_dim}). "
                        "Disconnected operational components. Information not flowing."}
    else:
        return {"status": "FLAT",
                "note": "Trivial holonomy. Parallel transport consistent. No loop contradictions."}

def _translate_markov(top_node: str, weights: List[float], names: List[str]) -> Dict[str, Any]:
    top_idx = int(np.argmax(weights))
    bottom_idx = int(np.argmin(weights))
    return {
        "critical_node":   top_node,
        "critical_weight": round(weights[top_idx], 4),
        "weakest_node":    names[bottom_idx],
        "weakest_weight":  round(weights[bottom_idx], 4),
        "note": (f"'{top_node}' carries {weights[top_idx]*100:.1f}% of Markov weight "
                 f"— single-point coherence bottleneck. "
                 f"'{names[bottom_idx]}' is most isolated ({weights[bottom_idx]*100:.1f}%)."),
    }

def _gate_from_ks(ks: Dict[str, Any]) -> str:
    """Combine all signals into a single gate decision."""
    lam1    = ks.get("lambda_1_fiber", 0.0)
    z_gate  = ks.get("zeta_gate", "PASS")
    score   = ks.get("ks_fiber_score", 0.0)
    hol     = ks.get("fiber_holonomy_trace", 0.0)
    h_dim   = ks.get("harmonic_dim", 0)
    d       = ks.get("fiber_dim", FIBER_DIM)

    # λ₁ thresholds from GATE_HALT_LAMBDA / GATE_WARN_LAMBDA (fiber_sheaf_engine.py)
    if lam1 < GATE_HALT_LAMBDA or z_gate == "HALT_A4" or score < 0.2:
        return "HALT_A4"
    if lam1 < GATE_WARN_LAMBDA or z_gate == "WARN" or hol > 8.0 or h_dim > d * 2:
        return "WARN"
    return "PASS"


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class ComputeDispatch:
    """
    Routes FiberSheafEngine operations to the appropriate tier
    and translates the output into operational language.

    Usage:
        dispatch = ComputeDispatch(tier=Tier.STANDARD)

        # From pre-built engine:
        result = dispatch.run(engine)

        # Auto-tier from context:
        result = ComputeDispatch.auto(engine, context="shift_handoff")

        # Translation only (already have ks dict):
        translated = ComputeDispatch.translate(ks_dict)

    Contexts → auto tier:
        "realtime"      → FAST     (mid-operation, A4 monitoring)
        "shift_handoff" → STANDARD (every 12 hours)
        "morning_report"→ FULL     (end-of-day DDR)
        "ddr"           → FULL
        "background"    → FULL
    """

    CONTEXT_TIER: Dict[str, Tier] = {
        "realtime":       Tier.FAST,
        "alarm":          Tier.FAST,
        "a4_check":       Tier.FAST,
        "shift_handoff":  Tier.STANDARD,
        "hourly":         Tier.STANDARD,
        "batch":          Tier.STANDARD,
        "morning_report": Tier.FULL,
        "ddr":            Tier.FULL,
        "end_of_day":     Tier.FULL,
        "background":     Tier.FULL,
    }

    def __init__(self, tier: Tier = Tier.STANDARD):
        self.tier = tier

    # ── Core run ──────────────────────────────────────────────────────────────

    def run(self, engine: FiberSheafEngine) -> Dict[str, Any]:
        """
        Execute operations according to tier plan, return enriched + translated K(S).
        """
        n = engine.bundle.n
        d = engine.bundle.d
        plan = OpPlan.for_tier(self.tier, n, d)

        t_start = time.perf_counter()
        ks: Dict[str, Any] = {}

        # ── Always: sheaf Laplacian + eigendecompose ──────────────────────────
        L_F          = engine.sheaf_ops.build_block_laplacian()
        evals, evecs = engine.sheaf_ops.eigendecompose()
        lam1_f       = engine.sheaf_ops.lambda_1_fiber()
        h_dim        = engine.sheaf_ops.harmonic_dim()
        hol_trace    = engine.sheaf_ops.fiber_holonomy_trace()

        ks.update({
            "tier":                 plan.tier,
            "fiber_dim":            d,
            "n_nodes":              n,
            "node_names":           engine.bundle.node_names,
            "lambda_1_fiber":       round(lam1_f, 8),
            "harmonic_dim":         h_dim,
            "fiber_holonomy_trace": round(hol_trace, 6),
            "eigenvalues_top8":     [round(float(e), 6) for e in evals[:8]],
        })

        # ── Always: cheap zeta ops ────────────────────────────────────────────
        zeta_coh  = ZetaSpectralEmbedder.zeta_coherence(evals)
        prime_res = ZetaSpectralEmbedder.prime_resonance(evals)
        zeta_emb  = ZetaSpectralEmbedder.zeta_embedding_vector(evals)
        z_gate    = ZetaSpectralEmbedder.zeta_gate(evals)

        ks.update({
            "zeta_coherence":    round(zeta_coh, 6),
            "prime_resonance":   round(prime_res, 6),
            "zeta_embedding":    [round(float(x), 6) for x in zeta_emb],
            "zeta_embedding_dim":len(zeta_emb),
            "zeta_gate":         z_gate,
        })

        # ── STANDARD+: Markov transition (no stationary) ─────────────────────
        if plan.run_markov_T:
            T = engine.sheaf_ops.build_markov_transition()
            # Cheap proxy for node importance: row L2 norms of T
            _nd = T.shape[0]
            proxy_w = np.array([
                float(np.linalg.norm(T[v*d:(v+1)*d, :]))
                for v in range(n)
            ])
            proxy_w /= proxy_w.sum() + 1e-14
            top_node = engine.bundle.node_names[int(np.argmax(proxy_w))]
            ks["markov_node_weights"] = [round(float(w), 6) for w in proxy_w]
            ks["markov_top_node"]     = top_node
        else:
            # FAST fallback: use Laplacian row-norm as proxy
            proxy_w = np.array([
                float(np.linalg.norm(L_F[v*d:(v+1)*d, :]))
                for v in range(n)
            ])
            proxy_w /= proxy_w.sum() + 1e-14
            ks["markov_node_weights"] = [round(float(w), 6) for w in proxy_w]
            ks["markov_top_node"]     = engine.bundle.node_names[int(np.argmax(proxy_w))]

        # ── FULL: Markov stationary + zeta_mat + diffusion ───────────────────
        if plan.run_markov_stat:
            pi       = engine.sheaf_ops.markov_stationary()
            stat_w   = np.array([float(np.linalg.norm(pi[v*d:(v+1)*d])) for v in range(n)])
            stat_w  /= stat_w.sum() + 1e-14
            ks["markov_node_weights"] = [round(float(w), 6) for w in stat_w]
            ks["markov_top_node"]     = engine.bundle.node_names[int(np.argmax(stat_w))]

        if plan.run_zeta_mat:
            L_zeta    = ZetaSpectralEmbedder.zeta_matricized(L_F)
            lam1_zeta = ZetaSpectralEmbedder.lambda1_zeta_laplacian(L_zeta)
            ks["lambda_1_zeta"] = round(lam1_zeta, 6)

        if plan.run_diffusion:
            diff = engine.sheaf_ops.markov_diffusion_map(t=3, k=4)
            ks["diffusion_coords"] = [[round(float(x), 6) for x in row] for row in diff]

        # ── Composite score ───────────────────────────────────────────────────
        ks_score = (
            math.tanh(lam1_f * 10) * 0.40 +
            min(1.0, zeta_coh)     * 0.35 +
            prime_res              * 0.25
        )
        ks["ks_fiber_score"] = round(ks_score, 6)

        # ── Gate ──────────────────────────────────────────────────────────────
        ks["gate"] = _gate_from_ks(ks)

        # ── Timing ───────────────────────────────────────────────────────────
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        ks["compute_ms"]      = round(elapsed_ms, 2)
        ks["estimated_ms"]    = plan.estimated_ms
        ks["plan_tier"]       = plan.tier

        # ── Translation ───────────────────────────────────────────────────────
        ks["translation"] = self.translate(ks)

        return ks

    # ── Translation ───────────────────────────────────────────────────────────

    @staticmethod
    def translate(ks: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw K(S) dict into a structured operational translation.
        Every mathematical output → human-readable, action-oriented language.
        """
        lam1    = ks.get("lambda_1_fiber", 0.0)
        z_coh   = ks.get("zeta_coherence", 0.0)
        p_res   = ks.get("prime_resonance", 0.0)
        hol     = ks.get("fiber_holonomy_trace", 0.0)
        h_dim   = ks.get("harmonic_dim", 0)
        d       = ks.get("fiber_dim", FIBER_DIM)
        gate    = ks.get("gate", "PASS")
        z_gate  = ks.get("zeta_gate", "PASS")   # required: used in trigger logic below
        weights = ks.get("markov_node_weights", [])
        names   = ks.get("node_names", [])
        score   = ks.get("ks_fiber_score", 0.0)
        top     = ks.get("markov_top_node", "—")

        lam_t   = _translate_lambda1(lam1)
        zeta_t  = _translate_zeta_coherence(z_coh)
        prime_t = _translate_prime_resonance(p_res)
        hol_t   = _translate_holonomy(hol, h_dim, d)
        mkv_t   = _translate_markov(top, weights, names) if weights and names else {}

        # Priority narrative
        # Determine primary trigger for the gate decision
        lam1_is_trigger  = lam1 < 0.01
        hol_is_trigger   = hol > 8.0 or h_dim > d * 2
        _zeta_is_trigger = z_gate in ("HALT_A4", "WARN")

        if gate == "HALT_A4":
            if lam1_is_trigger:
                trigger_note = lam_t['action']
            elif hol_is_trigger:
                trigger_note = hol_t['note'][:80]
            else:
                trigger_note = f"Zeta gate: {z_gate}. {zeta_t['note'][:60]}"
            narrative = (
                f"⛔ HALT — A4 TRIGGERED. λ₁={lam1:.4f}  score={score:.3f}. "
                f"{trigger_note} "
                f"Critical node: {top}. Zeta: {zeta_t['regime']}."
            )
        elif gate == "WARN":
            if hol_is_trigger and not lam1_is_trigger:
                trigger_note = f"Holonomy {hol_t['status']} (trace={hol:.2f}). {hol_t['note'][:70]}"
            elif lam1_is_trigger:
                trigger_note = lam_t['action']
            else:
                trigger_note = f"Zeta {z_gate}. {zeta_t['note'][:60]}"
            narrative = (
                f"⚠️  WARN — λ₁={lam1:.4f}  score={score:.3f}. "
                f"{trigger_note} "
                f"Monitor: {top}."
            )
        else:
            narrative = (
                f"✅ PASS — λ₁={lam1:.4f}  score={score:.3f}. "
                f"Zeta: {zeta_t['regime']}. {zeta_t['note'][:55]} "
                f"Advance per program."
            )

        return {
            "gate":      gate,
            "narrative": narrative,
            "lambda1": {
                "value":  round(lam1, 6),
                **lam_t,
            },
            "zeta": {
                "coherence": round(z_coh, 6),
                **zeta_t,
            },
            "prime": {
                "resonance": round(p_res, 6),
                "note":      prime_t,
            },
            "holonomy": {
                "trace": round(hol, 4),
                **hol_t,
            },
            "markov": mkv_t,
            "score":  round(score, 4),
        }

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def auto(
        cls,
        engine: FiberSheafEngine,
        context: str = "shift_handoff",
    ) -> Dict[str, Any]:
        """Run with tier auto-selected from operational context string."""
        tier = cls.CONTEXT_TIER.get(context, Tier.STANDARD)
        return cls(tier=tier).run(engine)

    @classmethod
    def from_afe(cls, afe_state: "AFEState",
                 context: str = "ddr") -> Dict[str, Any]:
        eng = FiberSheafEngine.from_afe(afe_state)
        return cls.auto(eng, context)

    @classmethod
    def from_well(cls, well_state: "WellState",
                  context: str = "shift_handoff") -> Dict[str, Any]:
        eng = FiberSheafEngine.from_well(well_state)
        return cls.auto(eng, context)


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC BACKGROUND RUNNER  (FULL tier without blocking the hot path)
# ─────────────────────────────────────────────────────────────────────────────

class BackgroundSheaf:
    """
    Runs FULL-tier computation in a background thread.
    The main thread uses FAST result immediately;
    FULL result is available via .get() when ready.

    Pattern for real-time rig floor use:
        bg = BackgroundSheaf(engine)
        fast_ks = bg.fast()       # < 2ms, returns immediately
        ...                       # do UI work, log FAST result
        full_ks = bg.get(timeout=10.0)  # blocks until FULL is ready
    """

    def __init__(self, engine: FiberSheafEngine):
        self._engine  = engine
        self._fast_ks: Optional[Dict[str, Any]] = None
        self._full_ks: Optional[Dict[str, Any]] = None
        self._event   = threading.Event()
        self._thread  = threading.Thread(target=self._run_full, daemon=True)
        self._thread.start()

    def fast(self) -> Dict[str, Any]:
        """Return FAST result synchronously (< 2ms)."""
        if self._fast_ks is None:
            self._fast_ks = ComputeDispatch(Tier.FAST).run(self._engine)
        return self._fast_ks

    def _run_full(self) -> None:
        self._full_ks = ComputeDispatch(Tier.FULL).run(self._engine)
        self._event.set()

    def get(self, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Block until FULL result is ready, or return None on timeout."""
        self._event.wait(timeout=timeout)
        return self._full_ks

    def is_ready(self) -> bool:
        return self._event.is_set()


# ─────────────────────────────────────────────────────────────────────────────
# DELTA DISPATCH — compare two states
# ─────────────────────────────────────────────────────────────────────────────

def dispatch_delta(
    prior_engine:   FiberSheafEngine,
    current_engine: FiberSheafEngine,
    context: str = "shift_handoff",
) -> Dict[str, Any]:
    """
    Compute and translate the delta K(S) between two operational states.
    Returns enriched delta with gate + human-readable change summary.
    """
    prior_ks   = ComputeDispatch.auto(prior_engine,   context)
    current_ks = ComputeDispatch.auto(current_engine, context)
    delta      = compute_delta_fiber(prior_ks, current_ks)

    d_lam   = delta["delta_lambda_1_fiber"]
    d_score = delta["delta_ks_fiber_score"]
    gate    = delta["gate"]

    if gate == "HALT_A4":
        delta["narrative"] = (
            f"⛔ A4 — Δλ₁={d_lam:+.4f}  Δscore={d_score:+.3f}. "
            f"Coherence regression. Halt and investigate before next advance."
        )
    elif gate == "WARN":
        delta["narrative"] = (
            f"⚠️  WARN — Δλ₁={d_lam:+.4f}  Δscore={d_score:+.3f}. "
            f"Coherence declining. Log to DDR. Check critical node."
        )
    else:
        delta["narrative"] = (
            f"✅ PASS — Δλ₁={d_lam:+.4f}  Δscore={d_score:+.3f}. "
            f"Coherence stable or improving."
        )

    delta["prior_ks"]   = prior_ks
    delta["current_ks"] = current_ks
    return delta
