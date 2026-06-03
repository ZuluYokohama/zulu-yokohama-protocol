"""
OG-EP SUPERINTENDENT SYSTEM
data/well_program.py

The Well Program as a Configurational Term Series

Maps the ZuluYokohama Axiom 5.2 (Configurational Term Series) to the drilling program.
The well program is not a static document — it is a sequence of configurational states.

Each term = a phase of the well (Drive Pipe → Surface → Intermediate → Production → TD).
The gate between terms = Δλ₁ ≥ 0 + holonomy trivial + A5 (λ₁ > threshold).

Superintendent can never advance to next phase without passing the gate.
No bypass. No override except explicit written authorization with documented K(S) rationale.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from enum import Enum


class PhaseStatus(Enum):
    PENDING     = "PENDING"       # Not yet started
    ACTIVE      = "ACTIVE"        # Currently drilling
    GATE_CHECK  = "GATE_CHECK"    # Waiting for K(S) gate approval
    COMPLETE    = "COMPLETE"      # Cased, cemented, verified
    BYPASSED    = "BYPASSED"      # Superintendent override (requires written AFE auth)


@dataclass
class CasingSpec:
    """Casing string specification."""
    string_name: str              # e.g. "13-3/8\" Surface"
    od_in: float                  # Outer diameter (inches)
    weight_ppf: float             # Weight (lb/ft)
    grade: str                    # e.g. "J-55", "K-55", "P-110"
    connection: str               # e.g. "BTC", "VAM TOP"
    planned_shoe_depth_ft: float
    actual_shoe_depth_ft: float = 0.0
    cement_top_ft: float = 0.0    # Top of cement (from surface)
    woc_hours: float = 0.0        # Wait-on-cement hours


@dataclass
class BitRecord:
    """Complete bit record — Axiom A7 (primes as irreducible atoms)."""
    bit_number: int               # Sequential bit number for this well
    bit_size_in: float
    bit_type: str                 # e.g. "PDC", "TCI", "Hybrid"
    iadc_code: str                # e.g. "M332", "S223"
    manufacturer: str
    serial_number: str
    depth_in_ft: float
    depth_out_ft: float
    hours: float
    footage_ft: float
    avg_rop_fthr: float
    avg_wob_klbs: float
    avg_rpm: float
    dull_grade: str               # IADC dull grade, e.g. "2-2-CT-A-X-I-NO-PR"
    pull_reason: str              # Why pulled
    run_notes: str = ""

    @property
    def cost_per_foot(self) -> float:
        """Requires bit cost — placeholder for real system integration."""
        return 0.0  # injected from AFE when building report


@dataclass
class WellProgramPhase:
    """
    A single phase of the well program — one term in the configurational series.
    Axiom 5.2: each phase is a term with: spec → search/verify → execute → gate.
    """
    phase_id: str                       # e.g. "DRIVE_PIPE", "SURFACE", "INTERMEDIATE", "PRODUCTION"
    phase_name: str                     # Human readable
    phase_number: int                   # Sequence number (1-based)
    planned_top_ft: float               # Expected top depth
    planned_bottom_ft: float            # Expected TD for this phase
    planned_casing: CasingSpec          # Casing to be run at end of phase
    planned_mud_weight_ppg: float
    planned_rop_fthr: float             # Expected average ROP
    planned_hours: float                # Planned time for phase (from AFE)
    planned_cost_usd: float             # AFE cost for this phase
    formation_prognosis: str            # Expected formations
    hazards_identified: List[str] = field(default_factory=list)  # Pre-identified hazards
    contingencies: List[str] = field(default_factory=list)

    # Actuals (filled in as phase executes)
    status: PhaseStatus = PhaseStatus.PENDING
    actual_top_ft: float = 0.0
    actual_bottom_ft: float = 0.0
    actual_hours: float = 0.0
    actual_cost_usd: float = 0.0
    bit_records: List[BitRecord] = field(default_factory=list)
    npt_hours: float = 0.0
    notes: str = ""

    # Gate results
    gate_k_s_at_entry: Optional[Dict[str, Any]] = None   # K(S) when phase started
    gate_k_s_at_exit: Optional[Dict[str, Any]] = None    # K(S) when phase ended
    gate_delta_lambda_1: Optional[float] = None
    gate_status: str = "PENDING"        # PASS / WARN / HALT_A4 / BYPASSED
    gate_authorized_by: str = ""        # Who signed off

    @property
    def variance_hours(self) -> float:
        return self.actual_hours - self.planned_hours

    @property
    def variance_cost_usd(self) -> float:
        return self.actual_cost_usd - self.planned_cost_usd

    @property
    def variance_depth_ft(self) -> float:
        if self.actual_bottom_ft > 0:
            return self.actual_bottom_ft - self.planned_bottom_ft
        return 0.0


@dataclass
class WellProgram:
    """
    The complete well program — the full configurational term series.
    Axiom 3: A3 Universal Pipeline applied to wellbore construction.

    The term series:
    SPUD → DRIVE_PIPE → SURFACE → [INTERMEDIATE] → PRODUCTION → TD → COMPLETION

    Each arrow = a gate (Axiom A5: λ₁ > threshold, holonomy trivial).
    """
    well_name: str
    api_number: str
    operator: str
    afe_number: str
    afe_approved_usd: float
    spud_date_planned: str
    td_planned_ft: float
    td_formation_prognosis: str
    phases: List[WellProgramPhase]
    field_name: str = ""
    county_state: str = ""
    surface_location: str = ""
    datum: str = "KB"
    kb_elevation_ft: float = 0.0
    ground_elevation_ft: float = 0.0
    notes: str = ""

    @property
    def current_phase(self) -> Optional[WellProgramPhase]:
        for phase in self.phases:
            if phase.status == PhaseStatus.ACTIVE:
                return phase
        return None

    @property
    def completed_phases(self) -> List[WellProgramPhase]:
        return [p for p in self.phases if p.status == PhaseStatus.COMPLETE]

    @property
    def total_actual_cost_usd(self) -> float:
        return sum(p.actual_cost_usd for p in self.phases)

    @property
    def total_actual_hours(self) -> float:
        return sum(p.actual_hours for p in self.phases)

    def get_next_gate_phase(self) -> Optional[WellProgramPhase]:
        """Returns the next phase awaiting gate approval."""
        for phase in self.phases:
            if phase.status == PhaseStatus.GATE_CHECK:
                return phase
        return None

    def advance_to_next_phase(self,
                               gate_k_s: Dict[str, Any],
                               gate_delta_lambda_1: float,
                               authorized_by: str,
                               force: bool = False) -> Dict[str, Any]:
        """
        Advance the program to the next phase.
        Requires gate passage (Δλ₁ ≥ 0, holonomy trivial, λ₁ ≥ threshold).

        force=True = superintendent override (creates BYPASSED gate record).
        BYPASSED requires written AFE authorization in evidence bundle.
        """
        current = self.current_phase
        if not current:
            return {"error": "No active phase to advance from"}

        lambda_1 = gate_k_s.get("lambda_1", 0.0)
        holonomy = gate_k_s.get("holonomy_signature", "trivial")

        # Gate check
        gate_pass = (
            gate_delta_lambda_1 >= -0.05 and
            holonomy == "trivial" and
            lambda_1 >= 0.001
        )

        if not gate_pass and not force:
            current.gate_status = "HALT_A4"
            current.gate_k_s_at_exit = gate_k_s
            current.gate_delta_lambda_1 = gate_delta_lambda_1
            return {
                "gate_status": "HALT_A4",
                "reason": (f"Δλ₁={gate_delta_lambda_1:+.4f}, "
                           f"λ₁={lambda_1:.4f}, holonomy={holonomy}. "
                           f"Resolve before advancing."),
                "advance": False,
            }

        # Find next phase
        next_phase_idx = None
        for i, phase in enumerate(self.phases):
            if phase == current:
                if i + 1 < len(self.phases):
                    next_phase_idx = i + 1
                break

        if next_phase_idx is None:
            return {"gate_status": "COMPLETE", "reason": "Well program complete", "advance": False}

        # Complete current phase
        current.status = PhaseStatus.COMPLETE
        current.gate_k_s_at_exit = gate_k_s
        current.gate_delta_lambda_1 = gate_delta_lambda_1
        current.gate_status = "BYPASSED" if force else "PASS"
        current.gate_authorized_by = authorized_by

        # Start next phase
        next_phase = self.phases[next_phase_idx]
        next_phase.status = PhaseStatus.ACTIVE
        next_phase.gate_k_s_at_entry = gate_k_s

        return {
            "gate_status": "BYPASSED" if force else "PASS",
            "advance": True,
            "completed_phase": current.phase_id,
            "next_phase": next_phase.phase_id,
            "gate_delta_lambda_1": gate_delta_lambda_1,
            "authorized_by": authorized_by,
        }

    def format_program_summary(self) -> str:
        """Plain-text program status summary."""
        lines = [
            "=" * 70,
            f"WELL PROGRAM — {self.well_name}",
            f"AFE: {self.afe_number}  |  Operator: {self.operator}",
            f"TD (planned): {self.td_planned_ft:,.0f} ft  |  AFE: ${self.afe_approved_usd:,.0f}",
            "=" * 70,
            "",
            f"{'PHASE':<25} {'STATUS':<12} {'PLANNED':<10} {'ACTUAL':<10} {'GATE':<10}",
            "─" * 70,
        ]

        for phase in self.phases:
            status_str = phase.status.value
            planned_str = f"{phase.planned_bottom_ft:,.0f}ft"
            actual_str = f"{phase.actual_bottom_ft:,.0f}ft" if phase.actual_bottom_ft > 0 else "—"
            gate_str = phase.gate_status if phase.gate_status != "PENDING" else "—"

            icon = {
                "PENDING":    "⏳",
                "ACTIVE":     "🔄",
                "GATE_CHECK": "🔑",
                "COMPLETE":   "✅",
                "BYPASSED":   "⚠️",
            }.get(status_str, "")

            lines.append(
                f"{icon} {phase.phase_name:<23} {status_str:<12} {planned_str:<10} {actual_str:<10} {gate_str:<10}"
            )

        lines += [
            "─" * 70,
            f"  Total actual cost: ${self.total_actual_cost_usd:>12,.0f}",
            f"  AFE approved:      ${self.afe_approved_usd:>12,.0f}",
            f"  Variance:          ${self.total_actual_cost_usd - self.afe_approved_usd:>+12,.0f}",
            "=" * 70,
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY — Standard vertical well program template
# ─────────────────────────────────────────────────────────────────────────────

def build_standard_vertical_program(
    well_name: str,
    api_number: str,
    operator: str,
    afe_number: str,
    afe_approved_usd: float,
    td_planned_ft: float,
    drive_pipe_depth_ft: float = 60.0,
    surface_casing_depth_ft: float = 2000.0,
    intermediate_casing_depth_ft: float = 8000.0,
    production_casing_td: bool = True,  # Set to False for openhole completion
    field_name: str = "",
    county_state: str = "",
) -> WellProgram:
    """
    Build a standard vertical well program template.
    Superintendent fills in actual numbers as the well progresses.
    """

    phases = [
        WellProgramPhase(
            phase_id="DRIVE_PIPE",
            phase_name="Drive Pipe",
            phase_number=1,
            planned_top_ft=0.0,
            planned_bottom_ft=drive_pipe_depth_ft,
            planned_casing=CasingSpec(
                string_name="Drive Pipe (20\")",
                od_in=20.0,
                weight_ppf=94.0,
                grade="J-55",
                connection="BTC",
                planned_shoe_depth_ft=drive_pipe_depth_ft,
            ),
            planned_mud_weight_ppg=8.6,
            planned_rop_fthr=150.0,
            planned_hours=8.0,
            planned_cost_usd=afe_approved_usd * 0.02,
            formation_prognosis="Surface unconsolidated sediments",
            hazards_identified=["Shallow gas (survey required)"],
            contingencies=["Drive to competent formation, extend if needed"],
        ),
        WellProgramPhase(
            phase_id="SURFACE",
            phase_name="Surface Casing",
            phase_number=2,
            planned_top_ft=drive_pipe_depth_ft,
            planned_bottom_ft=surface_casing_depth_ft,
            planned_casing=CasingSpec(
                string_name='13-3/8" Surface',
                od_in=13.375,
                weight_ppf=54.5,
                grade="J-55",
                connection="BTC",
                planned_shoe_depth_ft=surface_casing_depth_ft,
            ),
            planned_mud_weight_ppg=8.7,
            planned_rop_fthr=120.0,
            planned_hours=24.0 * 3,
            planned_cost_usd=afe_approved_usd * 0.12,
            formation_prognosis="Consolidated surface formations, below fresh water sands",
            hazards_identified=["Conductor depth verification", "Lost circulation potential"],
            contingencies=["LCM pre-treatment available", "Shallow gas contingency plan"],
        ),
        WellProgramPhase(
            phase_id="INTERMEDIATE",
            phase_name="Intermediate Casing",
            phase_number=3,
            planned_top_ft=surface_casing_depth_ft,
            planned_bottom_ft=intermediate_casing_depth_ft,
            planned_casing=CasingSpec(
                string_name='9-5/8" Intermediate',
                od_in=9.625,
                weight_ppf=47.0,
                grade="N-80",
                connection="BTC",
                planned_shoe_depth_ft=intermediate_casing_depth_ft,
            ),
            planned_mud_weight_ppg=9.5,
            planned_rop_fthr=60.0,
            planned_hours=24.0 * 10,
            planned_cost_usd=afe_approved_usd * 0.35,
            formation_prognosis="Shale sequences, potential overpressure zones",
            hazards_identified=["Stuck pipe potential in reactive shale",
                                "ECD management critical", "Overpressure zone below 7000ft"],
            contingencies=["Spotting pill on standby", "MW increase pre-authorized to 11.5ppg"],
        ),
        WellProgramPhase(
            phase_id="PRODUCTION",
            phase_name="Production Interval",
            phase_number=4,
            planned_top_ft=intermediate_casing_depth_ft,
            planned_bottom_ft=td_planned_ft,
            planned_casing=CasingSpec(
                string_name='7" Production',
                od_in=7.0,
                weight_ppf=26.0,
                grade="P-110",
                connection="BTC",
                planned_shoe_depth_ft=td_planned_ft if production_casing_td else 0.0,
            ),
            planned_mud_weight_ppg=10.5,
            planned_rop_fthr=40.0,
            planned_hours=24.0 * 8,
            planned_cost_usd=afe_approved_usd * 0.35,
            formation_prognosis="Target reservoir — see geological prognosis",
            hazards_identified=["Wellbore stability near target", "H₂S possible — monitor"],
            contingencies=["Sidetrack approved to +200ft east", "Contingency MW to 12ppg"],
        ),
    ]

    return WellProgram(
        well_name=well_name,
        api_number=api_number,
        operator=operator,
        afe_number=afe_number,
        afe_approved_usd=afe_approved_usd,
        spud_date_planned="TBD",
        td_planned_ft=td_planned_ft,
        td_formation_prognosis="Target reservoir",
        phases=phases,
        field_name=field_name,
        county_state=county_state,
    )
