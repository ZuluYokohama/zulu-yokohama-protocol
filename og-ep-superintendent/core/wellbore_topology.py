"""
OG-EP SUPERINTENDENT SYSTEM
core/wellbore_topology.py

The Wellbore K(S) Engine — PrimeTopologicalSpace adapted for Oil & Gas E&P.

Applies ZuluYokohama Protocol mathematics to wellbore state:
    K(S) = (dim_H0, lambda_1, holonomy_signature, ...)

    dim_H0  = number of wellbore intervals in "global agreement"
              (connected sections where plan == actual)
    lambda_1 = spectral gap = coherence velocity of the well
              (how fast problems dissipate vs accumulate)
    holonomy = "trivial" if operations are path-consistent
              (mudlogger, directional, plan all agree)
              "non-trivial:cycle-..." if contradictions detected

A4 fires when:
    - Δλ₁ < -0.5  (coherence regression — NPT event, over-AFE)
    - holonomy becomes non-trivial (contractor reports contradict)
    - H² obstruction (systemic formation issue, casing integrity)
    - H³ violation (well control — IRRECOVERABLE HALT)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import eigsh, svds

# ─────────────────────────────────────────────────────────────────────────────
# WELLBORE DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WellboreInterval:
    """
    A single wellbore interval — the atomic unit (Axiom 1.1 Substrate Principle).
    Each interval is a discrete, verifiable condition:state.
    """
    interval_id: str              # e.g. "SURF-CASING", "INTERMEDIATE-1", "PRODUCTION"
    top_depth_ft: float           # KB depth at top
    bottom_depth_ft: float        # KB depth at bottom (current if active)
    planned_bottom_ft: float      # Program depth
    formation: str                # e.g. "Surface Clay", "Frontier Sands", "Niobrara"
    mud_weight_ppg: float         # Current EMW
    rop_fthr: float               # Rate of penetration (ft/hr) — 0 if not drilling
    npt_hours: float              # Accumulated non-productive time in this interval
    is_cased: bool                # Casing run and cemented?
    is_active: bool               # Currently being drilled?

    @property
    def footage(self) -> float:
        return max(0.0, self.bottom_depth_ft - self.top_depth_ft)

    @property
    def program_completion(self) -> float:
        """0.0 → 1.0 completion vs. program depth."""
        planned_footage = max(1.0, self.planned_bottom_ft - self.top_depth_ft)
        return min(1.0, self.footage / planned_footage)

    @property
    def is_on_program(self) -> bool:
        return self.bottom_depth_ft <= self.planned_bottom_ft * 1.05  # 5% tolerance


@dataclass
class WellState:
    """
    Full wellbore state at a point in time — the system state x ∈ X.
    This is the input to the K(S) engine.
    """
    well_name: str
    api_number: str
    rig_name: str
    spud_date: str                    # ISO format
    timestamp: str                    # ISO format — this is the "save"
    current_depth_ft: float           # Current MD
    td_planned_ft: float              # Total depth per program
    afe_number: str
    afe_approved_usd: float
    afe_spent_usd: float
    intervals: list[WellboreInterval]
    active_bit: str                   # e.g. "12.25in PDC - 6B"
    bit_hours: float
    wob_klbs: float                   # Weight on bit
    rpm: float
    flow_rate_gpm: float
    ecd_ppg: float                    # Equivalent circulating density
    events_24hr: list[str] = field(default_factory=list)  # Any notable events

    @property
    def afe_burn_rate(self) -> float:
        """Fraction of AFE spent."""
        if self.afe_approved_usd <= 0:
            return 0.0
        return self.afe_spent_usd / self.afe_approved_usd

    @property
    def depth_fraction(self) -> float:
        """Fraction of TD reached."""
        if self.td_planned_ft <= 0:
            return 0.0
        return min(1.0, self.current_depth_ft / self.td_planned_ft)

    @property
    def cost_efficiency(self) -> float:
        """
        Are we burning cost proportionally to depth?
        1.0 = perfect. > 1.0 = over-budget for depth drilled. < 1.0 = under-budget.
        """
        if self.depth_fraction <= 0:
            return 1.0
        return self.afe_burn_rate / self.depth_fraction


# ─────────────────────────────────────────────────────────────────────────────
# WELLBORE TOPOLOGY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class WellboreCryptologicKey:
    """
    K(S) for a wellbore — the irreducible topological fingerprint.
    Axiom A1: K(S) = (dim_H0, λ₁, Hol(∇), β₀, β₁, ...)
    """
    def __init__(self,
                 dim_H0: int,
                 lambda_1: float,
                 holonomy_signature: str,
                 afe_coherence: float,
                 depth_coherence: float,
                 npt_density: float,
                 timestamp: str,
                 well_name: str):
        self.dim_H0 = dim_H0
        self.lambda_1 = lambda_1
        self.holonomy_signature = holonomy_signature
        self.afe_coherence = afe_coherence        # budget vs actual alignment
        self.depth_coherence = depth_coherence    # plan vs actual depth alignment
        self.npt_density = npt_density            # NPT hours / total hours
        self.timestamp = timestamp
        self.well_name = well_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "well_name": self.well_name,
            "timestamp": self.timestamp,
            "dim_H0": self.dim_H0,
            "lambda_1": round(self.lambda_1, 6),
            "holonomy_signature": self.holonomy_signature,
            "afe_coherence": round(self.afe_coherence, 4),
            "depth_coherence": round(self.depth_coherence, 4),
            "npt_density": round(self.npt_density, 4),
        }

    def __repr__(self):
        return (f"K({self.well_name}) @ {self.timestamp}: "
                f"H⁰={self.dim_H0}, λ₁={self.lambda_1:.4f}, "
                f"hol={self.holonomy_signature}, "
                f"afe_coh={self.afe_coherence:.3f}, npt={self.npt_density:.3f}")


class WellboreTopologyEngine:
    """
    The topological heart of the superintendent system.

    Computes K(S) from a WellState using the Sheaf Laplacian:
        - Nodes = wellbore intervals + cost centers + contractors
        - Edges = interfaces (contractor handoffs, formation transitions)
        - Restriction maps = how well each node agrees with its neighbors
        - L_F = δᵀδ (agreement Laplacian)
        - λ₁ = spectral gap (coherence velocity)
        - dim H⁰ = connected agreement components
        - holonomy = whether operations are path-consistent

    Axiom A5: λ₁ < threshold → DO NOT advance to next casing point.
    Axiom A4: non-trivial holonomy → HALT + emit contradicting K(S) to stderr.
    """

    LAMBDA_1_THRESHOLDS = {
        "strong":   0.10,   # High confidence — advance
        "moderate": 0.01,   # Proceed with caution
        "weak":     0.001,  # WARN — iterate (rig up contingency)
        "dead":     0.0,    # FAIL — do not advance
    }

    def __init__(self, well_state: WellState):
        self.state = well_state
        self._key: WellboreCryptologicKey | None = None
        self._laplacian: csr_matrix | None = None
        self._delta: csr_matrix | None = None

    # ── Graph construction ──────────────────────────────────────────────────

    def _build_wellbore_graph(self) -> tuple[csr_matrix, list[str]]:
        """
        Construct the sheaf graph for the well.

        Nodes:
            - One per wellbore interval (the geological sections)
            - One per active contractor (directional, mud engineer, mudlogger, casing crew)
            - One per major cost center (drilling, completion, rental, fuel)

        Edges (restriction maps):
            - Interval → next interval (formation transition interface)
            - Interval → contractor (contractor is responsible for this interval)
            - Contractor → cost center (contractor bills go to this AFE code)

        Restriction map values encode AGREEMENT between nodes:
            1.0 = perfect agreement (plan matches actual)
            0.5 = partial agreement (within tolerance)
            0.0 = no agreement (contradicting reports)
        """
        intervals = self.state.intervals
        n_intervals = len(intervals)

        # Build node list
        node_ids = [iv.interval_id for iv in intervals]
        # Append synthetic cost / contractor nodes
        node_ids += ["AFE_DRILLING", "AFE_RENTAL", "AFE_FUEL", "CONTRACTOR_DIRECTIONAL",
                     "CONTRACTOR_MUD", "CONTRACTOR_MUDLOG"]
        n = len(node_ids)

        rows, cols, vals = [], [], []

        # ── Interval-to-interval edges (formation transitions) ──────────────
        for i in range(n_intervals - 1):
            iv_curr = intervals[i]
            iv_next = intervals[i + 1]

            # Agreement = both intervals closed/confirmed vs. active
            if iv_curr.is_cased and not iv_next.is_active:
                agreement = 1.0   # cemented casing → perfect handoff
            elif iv_curr.is_cased and iv_next.is_active:
                agreement = 0.8   # active drilling on confirmed shoe
            else:
                agreement = 0.4   # open hole uncertainty

            rows += [i, i+1]
            cols += [i+1, i]
            vals += [agreement, agreement]

        # ── Active interval → AFE_DRILLING edge ──────────────────────────────
        active_idx = next((i for i, iv in enumerate(intervals) if iv.is_active), 0)
        afe_drill_idx = node_ids.index("AFE_DRILLING")
        # Agreement = how well cost efficiency is tracking (1.0 = on budget)
        afe_agreement = max(0.0, 1.0 - abs(1.0 - self.state.cost_efficiency))
        rows += [active_idx, afe_drill_idx]
        cols += [afe_drill_idx, active_idx]
        vals += [afe_agreement, afe_agreement]

        # ── Contractor nodes → active interval ───────────────────────────────
        dir_idx  = node_ids.index("CONTRACTOR_DIRECTIONAL")
        mud_idx  = node_ids.index("CONTRACTOR_MUD")
        mlog_idx = node_ids.index("CONTRACTOR_MUDLOG")

        # ECD coherence — mud weight vs. ECD → mud contractor agreement
        ecd_delta = abs(self.state.ecd_ppg - self.state.intervals[active_idx].mud_weight_ppg)
        mud_agreement = max(0.0, 1.0 - ecd_delta * 2.0)

        # ROP coherence — if drilling fast and WOB/RPM make sense → directional agreement
        rop_norm = min(1.0, self.state.intervals[active_idx].rop_fthr / 100.0)
        dir_agreement = rop_norm if self.state.wob_klbs > 0 else 0.3

        # Mudlog reports open hole — always connected to active interval
        mlog_agreement = 0.9 if self.state.intervals[active_idx].is_active else 0.5

        for (c_idx, agr) in [(dir_idx, dir_agreement), (mud_idx, mud_agreement), (mlog_idx, mlog_agreement)]:
            rows += [active_idx, c_idx]
            cols += [c_idx, active_idx]
            vals += [agr, agr]

        # Build sparse coboundary matrix δ (n × n adjacency weighted by agreement)
        delta = csr_matrix(
            (vals, (rows, cols)),
            shape=(n, n),
            dtype=np.float64
        ).tocsr()

        return delta, node_ids

    def _compute_laplacian(self, delta: csr_matrix) -> csr_matrix:
        """Proper graph Laplacian L = D − A from weighted adjacency.
        D = diag(row sums).  NOT delta.T @ delta (that is AᵀA, not L)."""
        diag_vals = np.array(delta.sum(axis=1)).flatten()
        n = delta.shape[0]
        D = csr_matrix((diag_vals, (np.arange(n), np.arange(n))), shape=delta.shape)
        return (D - delta).tocsr()

    # ── K(S) computation ───────────────────────────────────────────────────

    def compute_key(self) -> WellboreCryptologicKey:
        """
        Main entry point. Compute K(S) for the current WellState.
        Axiom A1: before any action compute K(S). After any action, recompute.
        """
        delta, _node_ids = self._build_wellbore_graph()
        self._delta = delta
        n = delta.shape[0]

        # ── Sheaf Laplacian ────────────────────────────────────────────────
        L = self._compute_laplacian(delta)
        self._laplacian = L

        # ── λ₁ (spectral gap) ─────────────────────────────────────────────
        try:
            evals, _ = eigsh(L, k=min(4, n-1), which="SM", tol=1e-8, maxiter=2000)
            evals = np.sort(np.abs(evals))
            lambda_1 = float(evals[1]) if len(evals) > 1 else 0.0
        except Exception:
            lambda_1 = 1e-6

        # ── dim H⁰ ────────────────────────────────────────────────────────
        try:
            _, s, _ = svds(L, k=min(6, n-1), which="SM", tol=1e-8)
            threshold = 1e-6 * max(s.max(), 1.0)
            dim_H0 = int(np.sum(s < threshold))
        except Exception:
            adj = (delta != 0).astype(int)
            n_comp, _ = connected_components(adj, directed=False)
            dim_H0 = n_comp

        # ── Holonomy detection ─────────────────────────────────────────────
        holonomy = self._detect_holonomy(delta, dim_H0, n)

        # ── Domain-specific coherence scores ──────────────────────────────
        afe_coherence = max(0.0, 1.0 - abs(1.0 - self.state.cost_efficiency))
        depth_coherence = self.state.depth_fraction  # how far vs. TD

        total_hours = max(1.0, sum(
            iv.footage / max(0.1, iv.rop_fthr) + iv.npt_hours
            for iv in self.state.intervals
        ))
        total_npt = sum(iv.npt_hours for iv in self.state.intervals)
        npt_density = total_npt / total_hours

        self._key = WellboreCryptologicKey(
            dim_H0=dim_H0,
            lambda_1=lambda_1,
            holonomy_signature=holonomy,
            afe_coherence=afe_coherence,
            depth_coherence=depth_coherence,
            npt_density=npt_density,
            timestamp=self.state.timestamp,
            well_name=self.state.well_name,
        )
        return self._key

    def _detect_holonomy(self, delta: csr_matrix, dim_H0: int, n: int) -> str:
        """
        Holonomy = path-dependency in the restriction maps.
        Axiom A4: non-trivial holonomy = structural contradiction in the wellbore.

        In O&G terms: the mudlogger's depth, the driller's depth, and the
        directional driller's depth/inclination all tell different stories.
        """
        adj = (delta != 0).astype(int).tocoo()
        n_comp, _labels = connected_components(
            csr_matrix((np.ones(len(adj.row)), (adj.row, adj.col)), shape=(n, n)),
            directed=False
        )
        cycle_density = (len(adj.row) / 2) / max(n, 1)

        # Check AFE coherence — if AFE is way off program, that's a non-trivial loop
        if self.state.cost_efficiency > 1.30:
            return f"non-trivial:afe-overrun-{self.state.cost_efficiency:.2f}x"

        # Check ECD vs. mud weight — dangerous if diverged
        if self.state.intervals:
            active = next((iv for iv in self.state.intervals if iv.is_active), None)
            if active and abs(self.state.ecd_ppg - active.mud_weight_ppg) > 0.5:
                return f"non-trivial:ecd-mw-divergence-{abs(self.state.ecd_ppg - active.mud_weight_ppg):.2f}ppg"

        if cycle_density > 1.5 and dim_H0 < n_comp:
            return f"non-trivial:cycle-density-{cycle_density:.2f}"

        return "trivial"

    # ── Delta K(S) and A4 gate ─────────────────────────────────────────────

    def compute_delta(self, prior_key: WellboreCryptologicKey) -> dict[str, Any]:
        """
        Compute Δλ₁ between prior K(S) and current K(S).
        Axiom A5: Δλ₁ < -0.5 → HALT, do not advance to next casing point.
        """
        current = self.compute_key()
        delta_lambda_1 = current.lambda_1 - prior_key.lambda_1

        gate_status = "PASS"
        if delta_lambda_1 < -0.5 or current.holonomy_signature != "trivial":
            gate_status = "HALT_A4"
        elif delta_lambda_1 < -0.1 or current.lambda_1 < self.LAMBDA_1_THRESHOLDS["weak"]:
            gate_status = "WARN"

        return {
            "prior_key": prior_key.to_dict(),
            "current_key": current.to_dict(),
            "delta_lambda_1": round(delta_lambda_1, 6),
            "gate_status": gate_status,
            "a4_triggered": gate_status == "HALT_A4",
            "advance_recommendation": gate_status == "PASS",
        }

    # ── H-level classification ─────────────────────────────────────────────

    def classify_event(self, event_description: str) -> dict[str, Any]:
        """
        Classify any wellbore event by its H-level obstruction class.
        Maps the Jones Framework Vol IV / SANS architecture to O&G events.

        H⁰ = Routine (make hole, trip, pump down)
        H¹ = Fixable locally (reamer pass, slickline, wiper trip)
        H² = Systemic (formation change, casing shoe failure, lost returns)
        H³ = AXIOM VIOLATION (well control, fire, H₂S) → sys.exit equivalent
        """
        desc_lower = event_description.lower()

        # H³ — Well control / safety (irrecoverable)
        h3_keywords = ["kick", "well control", "blowout", "h2s", "fire", "evacuat",
                       "shut in", "bop", "flow check"]
        # Short abbreviations matched as whole words to avoid substring false-positives
        # e.g. "sis" must not match "analysis", "basis", "casing shoe analysis"
        h3_abbr = ["sis", "sicp", "sidpp", "bop"]
        def _kw_hit(text: str) -> bool:
            for kw in h3_keywords:
                if kw in text:
                    return True
            for ab in h3_abbr:
                if f" {ab} " in f" {text} " or text.startswith(ab + " ") or text.endswith(" " + ab):
                    return True
            return False
        if _kw_hit(desc_lower):
            return {
                "h_level": "H³",
                "severity": "AXIOM_VIOLATION",
                "action": "IRRECOVERABLE — SHUT IN WELL. EVACUATE RIG FLOOR. CALL OIM.",
                "route": "REMOTE",
                "advance": False,
            }

        # H² — Systemic obstructions
        h2_keywords = ["lost circulation", "loss of returns", "wellbore instability",
                       "severe packoff", "casing integrity", "formation fracture",
                       "differential sticking", "formation change", "overpressure"]
        if any(kw in desc_lower for kw in h2_keywords):
            return {
                "h_level": "H²",
                "severity": "SYSTEMIC",
                "action": "Macro engineering response required. Halt local patching. Escalate to company man + drilling engineer.",
                "route": "REMOTE",
                "advance": False,
            }

        # H¹ — Local issues, fixable
        h1_keywords = ["packoff", "tight hole", "overpull", "drag", "torque",
                       "stuck", "reaming", "wiper trip", "bridging", "fill"]
        if any(kw in desc_lower for kw in h1_keywords):
            return {
                "h_level": "H¹",
                "severity": "LOCAL_FIXABLE",
                "action": "Apply local corrective action. Monitor Δλ₁. If no improvement → escalate to H².",
                "route": "LOCAL",
                "advance": False,
            }

        # H⁰ — Routine
        return {
            "h_level": "H⁰",
            "severity": "ROUTINE",
            "action": "Standard operations. Continue program.",
            "route": "LOCAL",
            "advance": True,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def compute_well_key(state: WellState) -> WellboreCryptologicKey:
    """Factory: compute K(S) for a well state. The single function the UI calls."""
    engine = WellboreTopologyEngine(state)
    return engine.compute_key()


def check_advance_gate(prior_state: WellState, current_state: WellState) -> dict[str, Any]:
    """
    The Δλ₁ gate — call before advancing to next casing point, next bit run, or
    committing a major AFE supplement.
    Returns full delta report with gate_status and a4_triggered flag.
    """
    prior_key = compute_well_key(prior_state)
    engine = WellboreTopologyEngine(current_state)
    return engine.compute_delta(prior_key)
