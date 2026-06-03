"""
OG-EP SUPERINTENDENT SYSTEM
core/ddr_harvester.py

Daily Drilling Report (DDR) Harvester — The O&G GeometryHarvester

Captures K(S)_problem ↔ K(S)_solution Shape Pairs from every DDR
where a problem was encountered and resolved with Δλ₁ ≥ 0.

These pairs become the training data for the edge formation-intelligence model
(QLoRA fine-tuning on ARM64 6GB UMA — the rig floor tablet).

Wormhole-Path 2 equivalent for O&G:
    Problem event  → K(S)_problem  (stuck pipe, lost returns, bit failure)
    Solution event → K(S)_solution (worked free, LCM pill, bit pull)
    Δλ₁ ≥ 0 on resolution → capture the pair → distillation fuel

Over time: the local AI learns YOUR formation, YOUR rig, YOUR crew.
The shape pairs are the memory of every problem solved on every well.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# DDR DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DDREntry:
    """
    A single Daily Drilling Report — the primary "save" unit.
    Axiom A7: Each DDR is an irreducible prime in the well's development history.
    """
    report_date: str              # ISO date
    report_number: int            # Sequential DDR number (spud = #1)
    well_name: str
    afe_number: str
    rig_name: str
    operator_rep: str             # Superintendent / company man on tour

    # Depth
    depth_start_ft: float        # Depth at start of report period
    depth_end_ft: float          # Depth at end of report period
    bit_size_in: float            # e.g. 12.25
    bit_description: str          # e.g. "6-blade PDC, 16mm cutters"
    bit_serial: str
    bit_hours_on: float           # Total bit hours at start
    bit_hours_off: float          # Total bit hours at end

    # Drilling parameters (averages for period)
    avg_wob_klbs: float
    avg_rpm: float
    avg_rop_fthr: float
    avg_flow_gpm: float
    avg_ecd_ppg: float
    mud_weight_in_ppg: float
    mud_weight_out_ppg: float

    # Time accounting (must sum to 24.0 * days in period)
    drilling_hours: float
    tripping_hours: float
    reaming_hours: float
    cementing_hours: float
    casing_hours: float
    wait_hours: float             # WOC, WOW, etc.
    npt_hours: float              # Non-productive time

    # Cost (day's charges)
    day_cost_usd: float
    cumulative_cost_usd: float
    afe_approved_usd: float

    # Operations narrative
    operations_24hr: str          # What happened (narrative)
    next_24hr_plan: str           # What's planned
    problems: List[str] = field(default_factory=list)     # Problem events
    corrective_actions: List[str] = field(default_factory=list)

    # K(S) snapshot (added by system)
    k_s_snapshot: Optional[Dict[str, Any]] = None
    delta_lambda_1: Optional[float] = None
    a4_triggered: bool = False

    @property
    def footage_drilled(self) -> float:
        return max(0.0, self.depth_end_ft - self.depth_start_ft)

    @property
    def total_hours(self) -> float:
        return (self.drilling_hours + self.tripping_hours + self.reaming_hours +
                self.cementing_hours + self.casing_hours + self.wait_hours + self.npt_hours)

    @property
    def npt_pct(self) -> float:
        if self.total_hours <= 0:
            return 0.0
        return self.npt_hours / self.total_hours

    @property
    def cost_per_foot(self) -> float:
        if self.footage_drilled <= 0:
            return 0.0
        return self.day_cost_usd / self.footage_drilled

    @property
    def afe_burn_pct(self) -> float:
        if self.afe_approved_usd <= 0:
            return 0.0
        return self.cumulative_cost_usd / self.afe_approved_usd


@dataclass
class ShapePair:
    """
    A K(S)_problem ↔ K(S)_solution pair — training fuel for the edge model.
    Equivalent to geometry_harvester.py shape_pairs.jsonl entries.
    """
    pair_id: str
    well_name: str
    timestamp: str
    problem_type: str             # e.g. "stuck_pipe", "lost_circulation", "bit_failure"
    problem_description: str
    solution_description: str
    k_s_problem: Dict[str, Any]   # WellboreCryptologicKey at time of problem
    k_s_solution: Dict[str, Any]  # WellboreCryptologicKey after resolution
    delta_lambda_1: float         # Must be ≥ 0 for capture
    depth_ft: float
    formation: str
    resolution_hours: float       # How long it took to fix
    cost_impact_usd: float        # Extra cost from the problem


# ─────────────────────────────────────────────────────────────────────────────
# DDR HARVESTER
# ─────────────────────────────────────────────────────────────────────────────

class DDRHarvester:
    """
    Captures DDRs and harvests shape pairs from resolved problems.

    Every DDR = a sequence-oriented "save" (Axiom: saves are sequence-oriented).
    Every resolved problem with Δλ₁ ≥ 0 = a shape pair for distillation.

    Ledger: evidence/shape_pairs.jsonl (one JSON object per line)
            evidence/ddrs/{well_name}/DDR_{number:04d}.json
    """

    def __init__(self, evidence_dir: str):
        self.evidence_dir = Path(evidence_dir)
        self.ddrs_dir = self.evidence_dir / "ddrs"
        self.shape_pairs_file = self.evidence_dir / "shape_pairs.jsonl"
        self.ddrs_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def save_ddr(self, ddr: DDREntry) -> Path:
        """
        Save a DDR as a sequence-oriented save.
        Returns path to the saved file.
        """
        well_dir = self.ddrs_dir / ddr.well_name.replace(" ", "_").replace("/", "-")
        well_dir.mkdir(parents=True, exist_ok=True)

        ddr_path = well_dir / f"DDR_{ddr.report_number:04d}_{ddr.report_date}.json"

        with open(ddr_path, "w") as f:
            json.dump(asdict(ddr), f, indent=2, default=str)

        print(f"[DDRHarvester] DDR #{ddr.report_number} saved: {ddr_path.name}")
        print(f"  Well: {ddr.well_name} | Date: {ddr.report_date}")
        print(f"  Footage: {ddr.footage_drilled:.0f}ft | "
              f"NPT: {ddr.npt_pct*100:.1f}% | "
              f"CPF: ${ddr.cost_per_foot:,.0f}/ft")
        if ddr.a4_triggered:
            print(f"  ⚠️  A4 TRIGGERED — Δλ₁={ddr.delta_lambda_1:+.4f}")

        return ddr_path

    def harvest_shape_pair(
        self,
        ddr: DDREntry,
        problem_type: str,
        problem_description: str,
        solution_description: str,
        k_s_problem: Dict[str, Any],
        k_s_solution: Dict[str, Any],
        delta_lambda_1: float,
        formation: str,
        resolution_hours: float,
        cost_impact_usd: float,
    ) -> Optional[ShapePair]:
        """
        Capture a shape pair from a resolved problem.
        Only harvests if Δλ₁ ≥ 0 (Wormhole-Path 2 rule: positive resolution only).
        """
        if delta_lambda_1 < 0:
            print(f"[DDRHarvester] Shape pair NOT captured: Δλ₁={delta_lambda_1:+.4f} < 0 "
                  f"(problem not fully resolved)")
            return None

        pair_id = f"{ddr.well_name}-DDR{ddr.report_number:04d}-{problem_type}-{ddr.report_date}"

        pair = ShapePair(
            pair_id=pair_id,
            well_name=ddr.well_name,
            timestamp=ddr.report_date,
            problem_type=problem_type,
            problem_description=problem_description,
            solution_description=solution_description,
            k_s_problem=k_s_problem,
            k_s_solution=k_s_solution,
            delta_lambda_1=delta_lambda_1,
            depth_ft=ddr.depth_end_ft,
            formation=formation,
            resolution_hours=resolution_hours,
            cost_impact_usd=cost_impact_usd,
        )

        # Append to the canonical ledger
        with open(self.shape_pairs_file, "a") as f:
            f.write(json.dumps(asdict(pair), default=str) + "\n")

        print(f"[DDRHarvester] ✅ Shape pair captured: {pair_id}")
        print(f"  Problem: {problem_type} | Δλ₁={delta_lambda_1:+.4f}")
        print(f"  Resolution: {resolution_hours:.1f}hrs | Cost impact: ${cost_impact_usd:,.0f}")

        return pair

    def get_shape_pair_count(self) -> int:
        """Count harvested shape pairs in the ledger."""
        if not self.shape_pairs_file.exists():
            return 0
        with open(self.shape_pairs_file) as f:
            return sum(1 for line in f if line.strip())

    def load_shape_pairs(self) -> List[Dict[str, Any]]:
        """Load all shape pairs from the ledger."""
        if not self.shape_pairs_file.exists():
            return []
        pairs = []
        with open(self.shape_pairs_file) as f:
            for line in f:
                if line.strip():
                    try:
                        pairs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return pairs

    def get_well_summary(self, well_name: str) -> Dict[str, Any]:
        """Get performance summary for a well from all its DDRs."""
        well_dir = self.ddrs_dir / well_name.replace(" ", "_").replace("/", "-")
        if not well_dir.exists():
            return {"error": f"No DDRs found for {well_name}"}

        ddrs = []
        for ddr_file in sorted(well_dir.glob("DDR_*.json")):
            with open(ddr_file) as f:
                ddrs.append(json.load(f))

        if not ddrs:
            return {"error": "No DDR files found"}

        total_footage = sum(d["depth_end_ft"] - d["depth_start_ft"] for d in ddrs)
        total_npt = sum(d["npt_hours"] for d in ddrs)
        total_hours = sum(d.get("total_hours", 24.0) for d in ddrs)
        total_cost = max(d["cumulative_cost_usd"] for d in ddrs) if ddrs else 0
        afe = ddrs[0]["afe_approved_usd"] if ddrs else 0

        a4_events = [d for d in ddrs if d.get("a4_triggered", False)]

        return {
            "well_name": well_name,
            "total_ddrs": len(ddrs),
            "spud_date": ddrs[0]["report_date"] if ddrs else "N/A",
            "total_footage_ft": round(total_footage, 0),
            "total_npt_hours": round(total_npt, 1),
            "npt_pct": round(total_npt / max(1, total_hours) * 100, 1),
            "total_cost_usd": round(total_cost, 2),
            "afe_approved_usd": round(afe, 2),
            "afe_variance_pct": round(
                (total_cost - afe) / max(1, afe) * 100, 1),
            "a4_events": len(a4_events),
            "shape_pairs_harvested": sum(
                1 for p in self.load_shape_pairs() if p.get("well_name") == well_name),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DDR REPORT FORMATTER
# ─────────────────────────────────────────────────────────────────────────────

def format_ddr_text(ddr: DDREntry) -> str:
    """
    Generate the plain-text DDR that goes to management / partner reports.
    This is what the superintendent would have typed in Word or emailed.
    Now auto-generated from structured data with K(S) appended.
    """
    afe_pct = ddr.afe_burn_pct * 100
    lines = [
        "=" * 70,
        f"DAILY DRILLING REPORT — {ddr.report_date}",
        f"Report No: {ddr.report_number}  |  Well: {ddr.well_name}",
        f"AFE: {ddr.afe_number}  |  Rig: {ddr.rig_name}",
        f"Operator Rep: {ddr.operator_rep}",
        "=" * 70,
        "",
        "DEPTH SUMMARY",
        f"  Depth (start):  {ddr.depth_start_ft:>8,.0f} ft",
        f"  Depth (end):    {ddr.depth_end_ft:>8,.0f} ft",
        f"  Footage drilled:{ddr.footage_drilled:>8,.0f} ft",
        "",
        "DRILLING PARAMETERS",
        f"  Bit: {ddr.bit_size_in}\" {ddr.bit_description} (S/N: {ddr.bit_serial})",
        f"  Bit Hours (on/off): {ddr.bit_hours_on:.1f} / {ddr.bit_hours_off:.1f}",
        f"  Avg WOB: {ddr.avg_wob_klbs:.1f} klbs  |  Avg RPM: {ddr.avg_rpm:.0f}",
        f"  Avg ROP: {ddr.avg_rop_fthr:.1f} ft/hr  |  Avg Flow: {ddr.avg_flow_gpm:.0f} gpm",
        f"  MW in/out: {ddr.mud_weight_in_ppg:.2f} / {ddr.mud_weight_out_ppg:.2f} ppg",
        f"  Avg ECD: {ddr.avg_ecd_ppg:.2f} ppg",
        "",
        "TIME ACCOUNTING",
        f"  Drilling:  {ddr.drilling_hours:>5.1f} hrs",
        f"  Tripping:  {ddr.tripping_hours:>5.1f} hrs",
        f"  Reaming:   {ddr.reaming_hours:>5.1f} hrs",
        f"  Cementing: {ddr.cementing_hours:>5.1f} hrs",
        f"  Casing:    {ddr.casing_hours:>5.1f} hrs",
        f"  Wait:      {ddr.wait_hours:>5.1f} hrs",
        f"  NPT:       {ddr.npt_hours:>5.1f} hrs  ({ddr.npt_pct*100:.1f}%)",
        f"  TOTAL:     {ddr.total_hours:>5.1f} hrs",
        "",
        "COST SUMMARY",
        f"  Day cost:      ${ddr.day_cost_usd:>12,.0f}",
        f"  Cumulative:    ${ddr.cumulative_cost_usd:>12,.0f}",
        f"  AFE approved:  ${ddr.afe_approved_usd:>12,.0f}",
        f"  AFE burned:    {afe_pct:>6.1f}%  {'⚠️ WARNING' if afe_pct > 80 else ''}",
        f"  Cost / ft:     ${ddr.cost_per_foot:>12,.0f}/ft",
        "",
        "OPERATIONS — LAST 24 HOURS",
        ddr.operations_24hr,
        "",
        "PLAN — NEXT 24 HOURS",
        ddr.next_24hr_plan,
    ]

    if ddr.problems:
        lines += ["", "PROBLEMS / NPT", *[f"  • {p}" for p in ddr.problems]]
    if ddr.corrective_actions:
        lines += ["", "CORRECTIVE ACTIONS", *[f"  • {a}" for a in ddr.corrective_actions]]

    # K(S) snapshot — the ZuluYokohama evidence bundle
    if ddr.k_s_snapshot:
        ks = ddr.k_s_snapshot
        lines += [
            "",
            "─" * 70,
            "WELLBORE COHERENCE SNAPSHOT [ZuluYokohama Protocol K(S)]",
            f"  dim H⁰: {ks.get('dim_H0', 'N/A')}  |  λ₁: {ks.get('lambda_1', 'N/A'):.4f}  |  Holonomy: {ks.get('holonomy_signature', 'N/A')}",
            f"  Δλ₁ (vs prior DDR): {ddr.delta_lambda_1:+.4f}" if ddr.delta_lambda_1 is not None else "",
            f"  AFE coherence: {ks.get('afe_coherence', 'N/A'):.3f}  |  NPT density: {ks.get('npt_density', 'N/A'):.3f}",
            "  A4 STATUS: 🔴 TRIGGERED — See corrective actions" if ddr.a4_triggered else "  A4 STATUS: ✅ CLEAR",
            "─" * 70,
        ]

    lines.append("=" * 70)
    return "\n".join(lines)
