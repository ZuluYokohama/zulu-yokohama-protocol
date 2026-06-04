"""
OG-EP SUPERINTENDENT SYSTEM
router/ops_bipartite_router.py

The Operations Bipartite Router — LOCAL vs REMOTE Decision Engine

Applies the ZuluYokohama BipartiteRouter logic to O&G operations.

LOCAL = Standard operations within the approved drilling program.
        Superintendent handles it at the rig floor.
        K(S) is coherent (λ₁ strong, holonomy trivial, H⁰ healthy).

REMOTE = Engineering escalation required.
         Company drilling engineer + drilling contractor technical team.
         Triggered by: H² obstruction, negative Δλ₁, holonomy divergence.

H³ = WELL CONTROL — NOT "remote". IMMEDIATE rig floor action.
     System issues the well control protocol verbatim. No routing delay.

The mathematics of the current wellbore state dictate who handles it
and at what level. Zero bypass of the gate.
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class RoutingDecision:
    route: str                      # "LOCAL" | "REMOTE" | "WELL_CONTROL"
    confidence: str                 # "HIGH" | "MODERATE" | "LOW"
    h_level: str                    # "H⁰" | "H¹" | "H²" | "H³"
    action_required: str
    escalation_contacts: list
    time_sensitivity: str           # "ROUTINE" | "URGENT" | "IMMEDIATE"
    topology_basis: Dict[str, Any]  # The K(S) that drove this decision


class OpsbipartiteRouter:
    """
    The hard routing decision engine for O&G operations.

    Receives a prompt (problem description) + topology (K(S) snapshot)
    and makes the irrevocable call: LOCAL or REMOTE.

    Based on the BipartiteRouter from bipartite_router_plugin/router_gateway.py
    adapted for the rig floor instead of the LLM routing context.
    """

    # AFE overrun threshold — 0-100 percentage scale (matches DDRHarvester.get_well_summary)
    OVERRUN_THRESHOLD_PCT = 20.0   # 20 % over AFE → REMOTE
    LOCAL_LAMBDA_MIN      = 0.01   # λ₁ below this → REMOTE

    @staticmethod
    def _fmt_float(v, spec: str = ".4f") -> str:
        """Format a numeric value or return 'N/A' if absent/non-numeric."""
        return format(v, spec) if isinstance(v, (int, float)) else "N/A"

    def __init__(self, well_name: str, afe_number: str, operator: str,
                 drilling_engineer_contact: str, rig_manager_contact: str):
        self.well_name = well_name
        self.afe_number = afe_number
        self.operator = operator
        self.drilling_engineer = drilling_engineer_contact
        self.rig_manager = rig_manager_contact

    def route(
        self,
        problem_description: str,
        k_s_current: Dict[str, Any],
        delta_lambda_1: float,
        h_level: str,
        afe_variance_pct: float = 0.0,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        The irrevocable routing decision.

        Args:
            afe_variance_pct: AFE overrun as a PERCENTAGE (0–100 scale).
                              Ratio callers (0.0–1.0) are auto-normalised.
        """
        if k_s_current is None:
            raise ValueError(
                "k_s_current is required; cannot route without a topology basis. "
                "Compute K(S) via WellboreTopologyEngine or FiberSheafEngine first."
            )
        # lambda_1: use None sentinel — missing K(S) must not silently trigger REMOTE
        lambda_1 = k_s_current.get("lambda_1")
        holonomy = k_s_current.get("holonomy_signature", "trivial")
        # afe_variance_pct: caller must pass percentage (0-100); no auto-normalise
        # to avoid 0.5% being ambiguously converted to 50%

        print(f"\n[OpsRouter] Routing: β₀(H⁰)={k_s_current.get('dim_H0')}, "
              f"λ₁={self._fmt_float(lambda_1)}, Δλ₁={delta_lambda_1:+.4f}, "
              f"holonomy={holonomy}, H-level={h_level}")

        # ── H³: WELL CONTROL — no routing, immediate ──────────────────────
        if h_level == "H³":
            print("[OpsRouter] ⚠️  H³ DETECTED — WELL CONTROL PROTOCOL ACTIVATED")
            return RoutingDecision(
                route="WELL_CONTROL",
                confidence="ABSOLUTE",
                h_level="H³",
                action_required=self._well_control_protocol(),
                escalation_contacts=[
                    "OIM (Offshore Installation Manager) / Tool Pusher",
                    "Company Man — IMMEDIATE",
                    f"Drilling Engineer: {self.drilling_engineer} — IMMEDIATE",
                    "Emergency Response Team",
                    "BOP Test / Drill last 30 days?",
                ],
                time_sensitivity="IMMEDIATE",
                topology_basis=k_s_current,
            )

        # ── H²: REMOTE — systemic, needs engineering ──────────────────────
        if h_level == "H²":
            print("[OpsRouter] Decision: REMOTE (H² systemic obstruction)")
            return RoutingDecision(
                route="REMOTE",
                confidence="HIGH",
                h_level="H²",
                action_required=(
                    f"Escalate to drilling engineer. H² obstruction detected: {problem_description}. "
                    f"Local patching will not resolve. Prepare full wellbore K(S) package for engineering review."
                ),
                escalation_contacts=[
                    f"Drilling Engineer: {self.drilling_engineer}",
                    f"Rig Manager: {self.rig_manager}",
                    "Drilling contractor technical team",
                    "Wellbore integrity specialist if casing/cement issue",
                ],
                time_sensitivity="URGENT",
                topology_basis=k_s_current,
            )

        # ── AFE overrun → REMOTE for new approval ─────────────────────────
        if afe_variance_pct > self.OVERRUN_THRESHOLD_PCT:
            print(f"[OpsRouter] Decision: REMOTE (AFE overrun {afe_variance_pct:.1f}%)")
            return RoutingDecision(
                route="REMOTE",
                confidence="HIGH",
                h_level="H¹",
                action_required=(
                    f"AFE supplement required before continuing. "
                    f"Variance: {afe_variance_pct:.1f}% over approved budget. "
                    f"File supplement, obtain management approval, then resume."
                ),
                escalation_contacts=[
                    f"Drilling Engineer: {self.drilling_engineer}",
                    "Operations Manager / Asset Team",
                    "Finance (AFE approval authority)",
                ],
                time_sensitivity="URGENT",
                topology_basis=k_s_current,
            )

        # ── Non-trivial holonomy → REMOTE for consistency resolution ──────
        if holonomy != "trivial":
            print(f"[OpsRouter] Decision: REMOTE (non-trivial holonomy: {holonomy})")
            return RoutingDecision(
                route="REMOTE",
                confidence="HIGH",
                h_level="H¹",
                action_required=(
                    f"Resolve data contradiction before proceeding. "
                    f"Holonomy: {holonomy}. Verify: mudlogger depth vs. driller's depth, "
                    f"survey ties, AFE codes vs. invoices. One contractor's data is wrong."
                ),
                escalation_contacts=[
                    "Mudlogger — verify depths",
                    "Directional driller — verify surveys",
                    f"Drilling Engineer: {self.drilling_engineer}",
                ],
                time_sensitivity="URGENT",
                topology_basis=k_s_current,
            )

        # ── Negative Δλ₁ with weak λ₁ → REMOTE ───────────────────────────
        if delta_lambda_1 < -0.5 or (lambda_1 is not None and lambda_1 < self.LOCAL_LAMBDA_MIN):
            print(f"[OpsRouter] Decision: REMOTE (Δλ₁={delta_lambda_1:+.4f}, λ₁={lambda_1:.4f})")
            return RoutingDecision(
                route="REMOTE",
                confidence="MODERATE",
                h_level="H¹",
                action_required=(
                    f"Coherence regression detected. Δλ₁={delta_lambda_1:+.4f}. "
                    f"Do not advance to next phase. Review last 4 hours of operations. "
                    f"Consult drilling engineer on root cause."
                ),
                escalation_contacts=[
                    f"Drilling Engineer: {self.drilling_engineer}",
                    "Drilling contractor toolpusher",
                ],
                time_sensitivity="URGENT",
                topology_basis=k_s_current,
            )

        # ── H¹: LOCAL with monitoring ──────────────────────────────────────
        if h_level == "H¹":
            print("[OpsRouter] Decision: LOCAL (H¹ fixable, monitor Δλ₁)")
            return RoutingDecision(
                route="LOCAL",
                confidence="MODERATE",
                h_level="H¹",
                action_required=(
                    f"Apply local corrective action per program. "
                    f"Monitor Δλ₁ every 6 hours. If no improvement → escalate. "
                    f"Problem: {problem_description}"
                ),
                escalation_contacts=[
                    "Driller on tour",
                    "Rig toolpusher",
                    f"Drilling Engineer: {self.drilling_engineer} — on standby",
                ],
                time_sensitivity="ROUTINE",
                topology_basis=k_s_current,
            )

        # ── H⁰: LOCAL, standard ops ───────────────────────────────────────
        print("[OpsRouter] Decision: LOCAL (H⁰ routine, high coherence)")
        return RoutingDecision(
            route="LOCAL",
            confidence="HIGH",
            h_level="H⁰",
            action_required=f"Continue per program. {problem_description or 'Standard operations.'}",
            escalation_contacts=[],
            time_sensitivity="ROUTINE",
            topology_basis=k_s_current,
        )

    def _well_control_protocol(self) -> str:
        return """
WELL CONTROL PROTOCOL — IMMEDIATE ACTION REQUIRED
═══════════════════════════════════════════════════
1. HANG OFF DRILL STRING — set slips, pick up kelly/TDS above rotary table
2. SPACE OUT — position tool joint above rotary table (prevent BOP closure on TJ)
3. SHUT IN WELL:
   a. Close annular preventer FIRST
   b. Open choke manifold
   c. Close upper pipe rams
   d. Confirm SICP and SIDPP on gauges
4. NOTIFY:
   - Driller notifies toolpusher / OIM
   - Company man notified IMMEDIATELY
   - Drilling engineer — phone call, not radio
5. READ PRESSURES:
   - Shut-in drill pipe pressure (SIDPP)
   - Shut-in casing pressure (SICP)
   - Estimated pit gain (bbls)
6. DO NOT ATTEMPT KILL until drilling engineer is on phone
7. DOCUMENT: Time of shut-in, pressures, pit gain, last MW, last survey depth

CONTACTS: See RoutingDecision.escalation_contacts
"""

    def format_routing_package(self, decision: RoutingDecision,
                                 problem_description: str) -> str:
        """
        Format the routing decision as a package for the superintendent.
        Clear, no jargon, just what to do and who to call.
        """
        lines = [
            "=" * 70,
            f"OPS ROUTING DECISION — {decision.h_level} Event",
            f"Well: {self.well_name}  |  AFE: {self.afe_number}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 70,
            "",
            f"ROUTE:    {decision.route}",
            f"SEVERITY: {decision.h_level}",
            f"TIME:     {decision.time_sensitivity}",
            "",
            "PROBLEM:",
            f"  {problem_description}",
            "",
            "ACTION REQUIRED:",
        ]

        for line in decision.action_required.strip().split("\n"):
            lines.append(f"  {line}")

        if decision.escalation_contacts:
            lines += ["", "NOTIFY:"]
            for contact in decision.escalation_contacts:
                lines.append(f"  → {contact}")

        lines += [
            "",
            "TOPOLOGICAL BASIS (K(S)):",
            f"  λ₁:       {self._fmt_float(decision.topology_basis.get('lambda_1'))}",
            f"  dim H⁰:   {decision.topology_basis.get('dim_H0', 'N/A')}",
            f"  Holonomy: {decision.topology_basis.get('holonomy_signature', 'N/A')}",
            "=" * 70,
        ]

        return "\n".join(lines)
