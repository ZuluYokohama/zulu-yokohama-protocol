"""
OG-EP SUPERINTENDENT SYSTEM
core/afe_laplacian.py

AFE Cost Topology — Budget Coherence Engine

Models the AFE (Authorization for Expenditure) as a sheaf over the cost graph.
Detects coherence loss between:
    - Approved AFE budget by cost code
    - Actual charges by vendor / cost code
    - Forecast-to-complete

When AFE coherence drops (Δλ₁_cost < 0) → A4 fires:
    - Emit contradictory cost K(S) to report
    - Block any new PO approvals until corrective action filed
    - Auto-draft AFE supplement for superintendent signature

Axiom G2 (Value Genesis): The AFE *is* the value function for the well.
The budget warps the geometry of every decision made at the rig floor.
High-value (on-budget) regions are compressed → easy to reach.
Over-budget regions are expanded → hard to reach without A4 approval.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh


# ─────────────────────────────────────────────────────────────────────────────
# AFE DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

# Standard O&G AFE cost codes (the ontological selection for this system)
STANDARD_COST_CODES = {
    "100": "Rig Day Rate",
    "110": "Rig Mobilization / Demobilization",
    "200": "Directional Drilling & MWD/LWD",
    "210": "Drilling Bits",
    "220": "Drilling Fluids (Mud System)",
    "230": "Mud Logging",
    "300": "Casing & Tubing",
    "310": "Wellhead & BOP Equipment",
    "320": "Cementing Services",
    "400": "Wireline / Perforating",
    "410": "Drill Stem Testing",
    "500": "Fuel & Water",
    "510": "Location & Road",
    "600": "Environmental & Regulatory",
    "700": "Contingency (5%)",
    "800": "Completion Equipment",
    "900": "Overhead & Administration",
}


@dataclass
class AFELineItem:
    """
    A single AFE line item — atomic cost unit.
    Axiom 1.1: discrete, verifiable, atomic condition:state.
    """
    cost_code: str
    description: str
    afe_approved_usd: float
    actual_to_date_usd: float
    forecast_to_complete_usd: float
    vendor: str = ""
    notes: str = ""

    @property
    def total_forecast_usd(self) -> float:
        return self.actual_to_date_usd + self.forecast_to_complete_usd

    @property
    def variance_usd(self) -> float:
        """Positive = over budget. Negative = under budget."""
        return self.total_forecast_usd - self.afe_approved_usd

    @property
    def variance_pct(self) -> float:
        if self.afe_approved_usd <= 0:
            return 0.0
        return self.variance_usd / self.afe_approved_usd

    @property
    def coherence_score(self) -> float:
        """
        How coherent is this line item? (0.0 = wildly over, 1.0 = perfectly on budget)
        This becomes the restriction map weight for this cost node.
        """
        v = abs(self.variance_pct)
        if v <= 0.05:   return 1.0   # ≤5% variance → coherent
        elif v <= 0.15: return 0.7   # ≤15% → acceptable
        elif v <= 0.30: return 0.4   # ≤30% → warning
        elif v <= 0.50: return 0.2   # ≤50% → critical
        else:           return 0.0   # >50% → incoherent


@dataclass
class AFEState:
    """Full AFE state at a point in time."""
    afe_number: str
    well_name: str
    operator: str
    timestamp: str
    line_items: List[AFELineItem]
    phase: str = "DRILLING"  # DRILLING, COMPLETION, WORKOVER

    @property
    def total_approved_usd(self) -> float:
        return sum(li.afe_approved_usd for li in self.line_items)

    @property
    def total_actual_usd(self) -> float:
        return sum(li.actual_to_date_usd for li in self.line_items)

    @property
    def total_forecast_usd(self) -> float:
        return sum(li.total_forecast_usd for li in self.line_items)

    @property
    def total_variance_usd(self) -> float:
        return self.total_forecast_usd - self.total_approved_usd

    @property
    def total_variance_pct(self) -> float:
        if self.total_approved_usd <= 0:
            return 0.0
        return self.total_variance_usd / self.total_approved_usd


# ─────────────────────────────────────────────────────────────────────────────
# AFE LAPLACIAN ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class AFELaplacian:
    """
    Computes the cost-topology K(S) for an AFE.

    Graph structure:
        Nodes = AFE line items (cost codes)
        Edges = Dependencies between cost codes:
            - Rig Day Rate ↔ Directional Drilling (both time-based)
            - Mud ↔ Mud Logging (both in-hole at same time)
            - Casing ↔ Cementing (sequential, must both be on budget)
            - Directional ↔ Bits (simultaneous, consume together)
        Restriction maps = coherence scores between dependent line items

    λ₁ of the cost Laplacian = how quickly an over-budget condition in one
    cost code propagates to affect others. Low λ₁ = isolated overruns.
    High λ₁ = systemic cost problem (everything is over).
    """

    # Cost code dependency graph (which codes are co-dependent)
    COST_DEPENDENCIES = [
        ("100", "200"),  # Rig rate ↔ Directional (both daily)
        ("100", "230"),  # Rig rate ↔ Mudlogging (both daily)
        ("200", "210"),  # Directional ↔ Bits (in-hole together)
        ("200", "220"),  # Directional ↔ Mud (in-hole together)
        ("220", "230"),  # Mud ↔ Mudlogging (both surface systems)
        ("300", "320"),  # Casing ↔ Cementing (sequential pair)
        ("310", "300"),  # Wellhead ↔ Casing (go in together)
        ("500", "100"),  # Fuel ↔ Rig rate (rig burns fuel)
    ]

    def __init__(self, afe_state: AFEState):
        self.state = afe_state
        self._code_to_idx: Dict[str, int] = {}
        self._lambda_1: Optional[float] = None
        self._laplacian: Optional[csr_matrix] = None

    def _build_cost_graph(self) -> Tuple[csr_matrix, List[str]]:
        """Build the cost dependency graph with restriction maps."""
        line_items = self.state.line_items
        codes = [li.cost_code for li in line_items]
        self._code_to_idx = {code: i for i, code in enumerate(codes)}
        n = len(codes)

        rows, cols, vals = [], [], []

        # Add edges for co-dependent cost codes
        for (code_a, code_b) in self.COST_DEPENDENCIES:
            if code_a in self._code_to_idx and code_b in self._code_to_idx:
                i = self._code_to_idx[code_a]
                j = self._code_to_idx[code_b]
                li_a = line_items[i]
                li_b = line_items[j]

                # Restriction map weight = geometric mean of coherence scores
                agreement = (li_a.coherence_score * li_b.coherence_score) ** 0.5

                rows += [i, j]
                cols += [j, i]
                vals += [agreement, agreement]

        # Isolated nodes get self-loop (Axiom 1.1 — they still exist)
        for i in range(n):
            if i not in rows:
                rows.append(i)
                cols.append(i)
                vals.append(line_items[i].coherence_score)

        delta = csr_matrix((vals, (rows, cols)), shape=(n, n), dtype=np.float64).tocsr()
        return delta, codes

    def compute_cost_key(self) -> Dict[str, Any]:
        """
        Compute K(S) for the AFE.
        Returns the cost topology fingerprint with λ₁, coherence, and variance flags.
        """
        delta, codes = self._build_cost_graph()
        # Proper graph Laplacian: L = D − A  (NOT delta.T @ delta)
        diag_vals = np.array(delta.sum(axis=1)).flatten()
        n = delta.shape[0]
        from scipy.sparse import diags as _sp_diags
        D = _sp_diags(diag_vals, format='csr')
        L = (D - delta).tocsr()
        L = (L + L.T) / 2   # symmetrise for numerical cleanliness
        n = L.shape[0]

        try:
            evals, _ = eigsh(L, k=min(4, n-1), which="SM", tol=1e-8, maxiter=2000)
            evals = np.sort(np.abs(evals))
            self._lambda_1 = float(evals[1]) if len(evals) > 1 else 0.0
        except Exception:
            self._lambda_1 = 1e-6

        # Over-budget line items (the "frustrated" nodes)
        over_budget = [
            li for li in self.state.line_items if li.variance_pct > 0.10
        ]
        critical_overruns = [
            li for li in over_budget if li.variance_pct > 0.30
        ]

        total_approved = self.state.total_approved_usd
        total_forecast = self.state.total_forecast_usd
        overall_variance = self.state.total_variance_pct

        # Gate decision
        if overall_variance > 0.25 or len(critical_overruns) >= 2:
            gate = "HALT_A4"
            message = (f"AFE overrun {overall_variance*100:.1f}% with "
                       f"{len(critical_overruns)} critical overruns. "
                       f"File AFE supplement before next PO approval.")
        elif overall_variance > 0.10 or self._lambda_1 < 0.01:
            gate = "WARN"
            message = f"AFE variance {overall_variance*100:.1f}% — monitor closely."
        else:
            gate = "PASS"
            message = f"AFE coherent. Variance: {overall_variance*100:.1f}%"

        return {
            "afe_number": self.state.afe_number,
            "well_name": self.state.well_name,
            "timestamp": self.state.timestamp,
            "lambda_1_cost": round(self._lambda_1, 6),
            "total_approved_usd": round(total_approved, 2),
            "total_actual_usd": round(self.state.total_actual_usd, 2),
            "total_forecast_usd": round(total_forecast, 2),
            "total_variance_usd": round(self.state.total_variance_usd, 2),
            "total_variance_pct": round(overall_variance * 100, 1),
            "over_budget_items": [
                {"code": li.cost_code, "desc": li.description,
                 "variance_pct": round(li.variance_pct * 100, 1),
                 "variance_usd": round(li.variance_usd, 2)}
                for li in over_budget
            ],
            "critical_overruns": len(critical_overruns),
            "gate_status": gate,
            "message": message,
        }

    def draft_afe_supplement(self, reason: str) -> Dict[str, Any]:
        """
        Auto-draft an AFE supplement when A4 fires.
        Superintendent reviews, adjusts numbers, signs.
        """
        cost_key = self.compute_cost_key()
        over_items = cost_key["over_budget_items"]

        supplement_lines = []
        for item in over_items:
            li = next((x for x in self.state.line_items
                       if x.cost_code == item["code"]), None)
            if li:
                supplement_lines.append({
                    "cost_code": item["code"],
                    "description": li.description,
                    "original_approved_usd": round(li.afe_approved_usd, 2),
                    "recommended_revised_usd": round(li.total_forecast_usd * 1.05, 2),
                    "additional_required_usd": round(
                        li.total_forecast_usd * 1.05 - li.afe_approved_usd, 2),
                    "justification": f"Actual-to-date ${li.actual_to_date_usd:,.0f} + FTC ${li.forecast_to_complete_usd:,.0f} exceed original estimate by {item['variance_pct']:.1f}%"
                })

        total_supplement = sum(s["additional_required_usd"] for s in supplement_lines)

        return {
            "document_type": "AFE_SUPPLEMENT",
            "afe_number": self.state.afe_number,
            "well_name": self.state.well_name,
            "operator": self.state.operator,
            "date": self.state.timestamp[:10],
            "reason": reason,
            "supplement_lines": supplement_lines,
            "total_additional_requested_usd": round(total_supplement, 2),
            "revised_total_afe_usd": round(self.state.total_approved_usd + total_supplement, 2),
            "prepared_by": "OG-EP SUPERINTENDENT SYSTEM (ZuluYokohama Protocol)",
            "status": "DRAFT — REQUIRES SUPERINTENDENT SIGNATURE",
        }
