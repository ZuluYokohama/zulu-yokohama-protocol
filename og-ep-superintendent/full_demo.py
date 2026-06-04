"""
OG-EP SUPERINTENDENT SYSTEM
full_demo.py

End-to-End Demo — The Feedback Loop

Simulates a well from spud to TD:
    1. Build well program (term series)
    2. Drill each phase (DDRs)
    3. Compute K(S) at each DDR
    4. Route decisions (LOCAL/REMOTE)
    5. Harvest shape pairs from resolved problems
    6. Detect A4 triggers and file AFE supplement

This is the "full_feedback_loop_demo.py" equivalent from the ZuluYokohama Protocol,
adapted to the O&G superintendent context.

Run: python full_demo.py
"""

from __future__ import annotations
import json
import sys
import os
from datetime import datetime, date, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.wellbore_topology import (
    WellboreTopologyEngine, WellboreInterval, WellState, compute_well_key
)
from core.afe_laplacian import AFELaplacian, AFEState, AFELineItem, STANDARD_COST_CODES
from core.ddr_harvester import DDRHarvester, DDREntry, format_ddr_text
from router.ops_bipartite_router import OpsbipartiteRouter
from ui.morning_report import quick_morning_report
from data.well_program import (
    WellProgram, WellProgramPhase, PhaseStatus,
    build_standard_vertical_program
)


# ─────────────────────────────────────────────────────────────────────────────
# DEMO WELL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

WELL_NAME    = "Blackstone Federal 1-28H"
API_NUMBER   = "33-053-00001-00-00"
OPERATOR     = "Frontier E&P LLC"
AFE_NUMBER   = "2026-FEP-001"
RIG_NAME     = "Nabors 453"
SUPT_NAME    = "Roy Tillman"
DRILL_ENG    = "Pete Garza (307) 555-0142"
RIG_MANAGER  = "Dave Kowalski (307) 555-0199"
TD_PLANNED   = 11500.0
AFE_AMOUNT   = 2_850_000.0

EVIDENCE_DIR = str(Path(__file__).parent / "evidence")


def build_demo_well_state(
    phase: str,
    depth_ft: float,
    rop: float = 45.0,
    npt_hrs: float = 0.0,
    cost_so_far: float = 0.0,
    ecd: float = 10.5,
    mw: float = 10.2,
    wob: float = 18.0,
    rpm: float = 120.0,
    events: list = None,
) -> WellState:
    """Build a WellState for demo purposes."""

    intervals = [
        WellboreInterval(
            interval_id="DRIVE_PIPE",
            top_depth_ft=0, bottom_depth_ft=60, planned_bottom_ft=60,
            formation="Surface Clay", mud_weight_ppg=8.6, rop_fthr=0,
            npt_hours=0, is_cased=True, is_active=False,
        ),
        WellboreInterval(
            interval_id="SURFACE",
            top_depth_ft=60, bottom_depth_ft=2000, planned_bottom_ft=2000,
            formation="Surface Sands / Pierre Shale", mud_weight_ppg=8.8, rop_fthr=0,
            npt_hours=0, is_cased=True, is_active=False,
        ),
        WellboreInterval(
            interval_id="INTERMEDIATE",
            top_depth_ft=2000,
            bottom_depth_ft=min(depth_ft, 8000) if phase == "INTERMEDIATE" else 8000,
            planned_bottom_ft=8000,
            formation="Niobrara / Carlile Shale", mud_weight_ppg=mw, rop_fthr=rop,
            npt_hours=npt_hrs if phase == "INTERMEDIATE" else 0,
            is_cased=(phase in ["PRODUCTION"]),
            is_active=(phase == "INTERMEDIATE"),
        ),
        WellboreInterval(
            interval_id="PRODUCTION",
            top_depth_ft=8000,
            bottom_depth_ft=depth_ft if phase == "PRODUCTION" else 8000,
            planned_bottom_ft=TD_PLANNED,
            formation="Frontier Sands", mud_weight_ppg=mw, rop_fthr=rop,
            npt_hours=npt_hrs if phase == "PRODUCTION" else 0,
            is_cased=False,
            is_active=(phase == "PRODUCTION"),
        ),
    ]

    return WellState(
        well_name=WELL_NAME,
        api_number=API_NUMBER,
        rig_name=RIG_NAME,
        spud_date="2026-06-01",
        timestamp=datetime.now().isoformat(),
        current_depth_ft=depth_ft,
        td_planned_ft=TD_PLANNED,
        afe_number=AFE_NUMBER,
        afe_approved_usd=AFE_AMOUNT,
        afe_spent_usd=cost_so_far,
        intervals=intervals,
        active_bit='8-1/2" PDC 6-blade 16mm',
        bit_hours=65.0,
        wob_klbs=wob,
        rpm=rpm,
        flow_rate_gpm=750,
        ecd_ppg=ecd,
        events_24hr=events or [],
    )


def run_demo():
    print("\n" + "=" * 70)
    print("OG-EP SUPERINTENDENT SYSTEM — END TO END DEMO")
    print(f"Well: {WELL_NAME}")
    print(f"AFE: {AFE_NUMBER}  |  Approved: ${AFE_AMOUNT:,.0f}")
    print("=" * 70)

    # ── 1. Build the well program ─────────────────────────────────────────
    print("\n[PHASE 0] Building well program...")
    program = build_standard_vertical_program(
        well_name=WELL_NAME,
        api_number=API_NUMBER,
        operator=OPERATOR,
        afe_number=AFE_NUMBER,
        afe_approved_usd=AFE_AMOUNT,
        td_planned_ft=TD_PLANNED,
        field_name="Powder River Basin",
        county_state="Campbell County, WY",
    )
    # Activate first real phase
    program.phases[0].status = PhaseStatus.COMPLETE  # drive pipe done
    program.phases[1].status = PhaseStatus.COMPLETE  # surface done
    program.phases[2].status = PhaseStatus.ACTIVE    # drilling intermediate
    print(program.format_program_summary())

    # ── 2. DDR Harvester setup ────────────────────────────────────────────
    harvester = DDRHarvester(EVIDENCE_DIR)
    router = OpsbipartiteRouter(
        well_name=WELL_NAME,
        afe_number=AFE_NUMBER,
        operator=OPERATOR,
        drilling_engineer_contact=DRILL_ENG,
        rig_manager_contact=RIG_MANAGER,
    )

    print("\n[PHASE 1] Computing baseline K(S) (Day 1 - Intermediate at 5,200ft)...")
    state_d1 = build_demo_well_state(
        phase="INTERMEDIATE", depth_ft=5200, rop=62, cost_so_far=450_000,
        ecd=9.6, mw=9.4, wob=20, rpm=130,
    )
    engine_d1 = WellboreTopologyEngine(state_d1)
    key_d1 = engine_d1.compute_key()
    print(f"  Baseline K(S): {key_d1}")

    # ── 3. Day 2 DDR — normal drilling ────────────────────────────────────
    print("\n[PHASE 2] DDR Day 2 — Normal drilling, 6,150ft...")
    state_d2 = build_demo_well_state(
        phase="INTERMEDIATE", depth_ft=6150, rop=58, cost_so_far=580_000,
        ecd=9.7, mw=9.4, wob=19, rpm=125,
    )
    engine_d2 = WellboreTopologyEngine(state_d2)
    delta_d2 = engine_d2.compute_delta(key_d1)
    print(f"  Δλ₁: {delta_d2['delta_lambda_1']:+.4f}  Gate: {delta_d2['gate_status']}")

    ddr_d2 = DDREntry(
        report_date=(date.today() - timedelta(days=1)).isoformat(),
        report_number=12,
        well_name=WELL_NAME, afe_number=AFE_NUMBER, rig_name=RIG_NAME,
        operator_rep=SUPT_NAME,
        depth_start_ft=5200, depth_end_ft=6150,
        bit_size_in=8.5, bit_description='PDC 6-blade 16mm', bit_serial="PDC-2024-441",
        bit_hours_on=48.0, bit_hours_off=72.0,
        avg_wob_klbs=19.0, avg_rpm=125, avg_rop_fthr=58, avg_flow_gpm=750,
        avg_ecd_ppg=9.7, mud_weight_in_ppg=9.4, mud_weight_out_ppg=9.5,
        drilling_hours=16.5, tripping_hours=0, reaming_hours=2.0,
        cementing_hours=0, casing_hours=0, wait_hours=1.5, npt_hours=4.0,
        day_cost_usd=128_000, cumulative_cost_usd=580_000, afe_approved_usd=AFE_AMOUNT,
        operations_24hr=(
            "Continued drilling 8-1/2\" hole from 5200ft to 6150ft (950ft). "
            "Encountered tight hole at 5840ft — reamed 3 stands, returned to "
            "rotary drilling. 4hrs NPT for tight hole reaming."
        ),
        next_24hr_plan=(
            "Continue drilling to 7500ft. Monitor ECD. Run wiper trip at 7000ft "
            "per program. Maintain MW 9.4-9.6ppg."
        ),
        problems=["Tight hole at 5840ft — reamed out, not recurring"],
        k_s_snapshot=engine_d2.compute_key().to_dict(),
        delta_lambda_1=delta_d2["delta_lambda_1"],
        a4_triggered=(delta_d2["gate_status"] == "HALT_A4"),
    )
    harvester.save_ddr(ddr_d2)

    # ── 4. Day 3 — TROUBLE. Packoff / stuck pipe scenario ────────────────
    print("\n[PHASE 3] DDR Day 3 — Packoff / Stuck Pipe at 7,240ft...")
    state_d3 = build_demo_well_state(
        phase="INTERMEDIATE", depth_ft=7240, rop=12, cost_so_far=740_000,
        ecd=10.1, mw=9.5, wob=5, rpm=60, npt_hrs=14,
        events=["PACKOFF at 7,240ft — pumps up on connections", "18 tons overpull"],
    )
    engine_d3 = WellboreTopologyEngine(state_d3)
    key_d3_problem = engine_d3.compute_key()
    delta_d3 = engine_d3.compute_delta(engine_d2.compute_key())
    print(f"  Δλ₁: {delta_d3['delta_lambda_1']:+.4f}  Gate: {delta_d3['gate_status']}")

    # Route the problem
    event_class = engine_d3.classify_event("packoff severe overpull 18 tons stuck")
    print(f"  H-level: {event_class['h_level']} — {event_class['action'][:60]}...")

    routing = router.route(
        problem_description="Packoff at 7,240ft. 18 tons overpull. Pumps up on connections. ECD 10.1ppg.",
        k_s_current=key_d3_problem.to_dict(),
        delta_lambda_1=delta_d3["delta_lambda_1"],
        h_level=event_class["h_level"],
        afe_variance_pct=0.05,
    )
    print(router.format_routing_package(routing, "Packoff at 7,240ft"))

    # ── 5. Day 4 — Problem resolved (worked free, LCM pill) ──────────────
    print("\n[PHASE 4] Resolution — Worked free, LCM pill, back to drilling...")
    state_d4 = build_demo_well_state(
        phase="INTERMEDIATE", depth_ft=7480, rop=42, cost_so_far=870_000,
        ecd=9.8, mw=9.6, wob=16, rpm=115, npt_hrs=2,
        events=["Worked free at 0430 after 6hr work string operation", "LCM pill pumped"],
    )
    engine_d4 = WellboreTopologyEngine(state_d4)
    key_d4_solution = engine_d4.compute_key()
    delta_d4 = engine_d4.compute_delta(key_d3_problem)
    print(f"  Δλ₁ (problem → solution): {delta_d4['delta_lambda_1']:+.4f}")

    # Harvest the shape pair — stuck pipe problem → resolution
    pair = harvester.harvest_shape_pair(
        ddr=DDREntry(
            report_date=date.today().isoformat(),
            report_number=14,
            well_name=WELL_NAME, afe_number=AFE_NUMBER, rig_name=RIG_NAME,
            operator_rep=SUPT_NAME,
            depth_start_ft=7240, depth_end_ft=7480,
            bit_size_in=8.5, bit_description='PDC 6-blade 16mm', bit_serial="PDC-2024-441",
            bit_hours_on=72.0, bit_hours_off=96.0,
            avg_wob_klbs=16, avg_rpm=115, avg_rop_fthr=42, avg_flow_gpm=750,
            avg_ecd_ppg=9.8, mud_weight_in_ppg=9.6, mud_weight_out_ppg=9.7,
            drilling_hours=10, tripping_hours=4, reaming_hours=6, cementing_hours=0,
            casing_hours=0, wait_hours=2, npt_hours=2,
            day_cost_usd=152_000, cumulative_cost_usd=870_000, afe_approved_usd=AFE_AMOUNT,
            operations_24hr="Worked free from packoff at 0430. Pumped LCM pill. POOH to 6500ft, wiper trip, back to bottom. Resumed drilling to 7480ft.",
            next_24hr_plan="Continue to 8000ft (9-5/8\" casing shoe). Pre-flush casing seat. Run shoe track.",
        ),
        problem_type="packoff_stuck_pipe",
        problem_description="Packoff at 7,240ft in Carlile shale, 18 tons overpull, ECD spike to 10.1ppg",
        solution_description="Worked free with 6hr work string rotation/reciprocation. LCM pill (20ppb mica/walnut) resolved losses. Back to drilling.",
        k_s_problem=key_d3_problem.to_dict(),
        k_s_solution=key_d4_solution.to_dict(),
        delta_lambda_1=delta_d4["delta_lambda_1"],
        formation="Carlile Shale",
        resolution_hours=18.0,
        cost_impact_usd=45_000,
    )

    if pair:
        print(f"  ✅ Shape pair harvested — distillation fuel added to ledger")

    # ── 6. Morning report ─────────────────────────────────────────────────
    print("\n[PHASE 5] Generating morning report...")
    morning = quick_morning_report(
        well_name=WELL_NAME,
        afe_number=AFE_NUMBER,
        depth_ft=7480,
        td_ft=TD_PLANNED,
        footage_24hr=240,
        on_bottom_hrs=10,
        bit='8-1/2" PDC 6B (S/N PDC-2024-441)',
        bit_hrs=96.0,
        mw_ppg=9.6,
        ecd_ppg=9.8,
        afe_approved=AFE_AMOUNT,
        afe_spent=870_000,
        ops_summary="Resolved packoff. LCM pill. Wiper trip. Back to drilling. 240ft in 10hr OB.",
        next_plan="Drill to 8000ft casing shoe. Pre-flush seat. Run 9-5/8\" string. Cement to surface.",
        problems=["Monitor ECD closely through remaining Carlile shale"],
    )
    print(morning)

    # ── 7. AFE status ─────────────────────────────────────────────────────
    print("\n[PHASE 6] AFE Coherence Check...")
    afe_state = AFEState(
        afe_number=AFE_NUMBER,
        well_name=WELL_NAME,
        operator=OPERATOR,
        timestamp=datetime.now().isoformat(),
        line_items=[
            AFELineItem("100", "Rig Day Rate", 950_000, 320_000, 490_000),
            AFELineItem("200", "Directional Drilling & MWD", 280_000, 95_000, 165_000),
            AFELineItem("210", "Drilling Bits", 85_000, 42_000, 35_000),
            AFELineItem("220", "Drilling Fluids", 180_000, 78_000, 95_000, notes="LCM treatment extra"),
            AFELineItem("230", "Mud Logging", 65_000, 22_000, 38_000),
            AFELineItem("300", "Casing & Tubing", 420_000, 38_000, 390_000),
            AFELineItem("320", "Cementing", 140_000, 12_000, 135_000),
            AFELineItem("310", "Wellhead & BOP", 85_000, 82_000, 0),
            AFELineItem("500", "Fuel & Water", 65_000, 30_000, 32_000),
            AFELineItem("700", "Contingency", 130_000, 0, 45_000, notes="Packoff event"),
        ]
    )
    afe_engine = AFELaplacian(afe_state)
    cost_key = afe_engine.compute_cost_key()
    print(json.dumps(cost_key, indent=2))

    # ── 8. Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DEMO COMPLETE — EVIDENCE LEDGER")
    print("=" * 70)
    print(f"  DDRs saved:         {len(list(Path(EVIDENCE_DIR + '/ddrs').rglob('*.json')))} files")
    print(f"  Shape pairs:        {harvester.get_shape_pair_count()}")
    print(f"  A4 events:          {1 if delta_d3['gate_status'] == 'HALT_A4' else 0}")
    print(f"  AFE gate status:    {cost_key['gate_status']}")
    print(f"  Final K(S) λ₁:      {key_d4_solution.lambda_1:.4f}")
    print(f"  Holonomy:           {key_d4_solution.holonomy_signature}")
    print()
    print("  Shape pairs written to: evidence/shape_pairs.jsonl")
    print("  DDRs written to:        evidence/ddrs/")
    print()
    print("  The mathematics are the operating system.")
    print("  The Anvil holds at the rig floor.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
