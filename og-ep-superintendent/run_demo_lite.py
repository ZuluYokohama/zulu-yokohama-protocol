"""
OG-EP SUPERINTENDENT SYSTEM
run_demo_lite.py

Zero-dependency demo — runs on any Python 3.8+ with NO pip installs.
Demonstrates the full workflow using topology_lite.py pure-Python engine.
"""

from __future__ import annotations
import json, sys, math
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.topology_lite import compute_well_key_lite

# ─────────────────────────────────────────────────────────────────────────────
WELL      = "Blackstone Federal 1-28H"
AFE_NO    = "2026-FEP-001"
OPERATOR  = "Frontier E&P LLC"
RIG       = "Nabors 453"
SUPT      = "Roy Tillman"
TD_FT     = 11_500.0
AFE_AMT   = 2_850_000.0
EVIDENCE  = Path(__file__).parent / "evidence"
EVIDENCE.mkdir(exist_ok=True)
(EVIDENCE / "ddrs").mkdir(exist_ok=True)
PAIRS_FILE = EVIDENCE / "shape_pairs.jsonl"

shape_pair_count = 0

# ─────────────────────────────────────────────────────────────────────────────
def sep(title=""):
    w = 70
    if title:
        pad = (w - len(title) - 2) // 2
        print("─" * pad + f" {title} " + "─" * (w - pad - len(title) - 2))
    else:
        print("─" * w)

def gate_label(gate):
    return {"PASS":"✅ PASS", "WARN":"🟡 WARN", "HALT_A4":"🔴 HALT_A4"}.get(gate, gate)

def h_route(desc_lower):
    h3 = ["kick","well control","blowout","h2s","fire","shut in","bop"]
    h2 = ["lost circulation","loss of returns","severe packoff","casing integrity",
          "differential sticking","formation fracture","overpressure"]
    h1 = ["packoff","tight hole","overpull","drag","torque","stuck","reaming",
          "wiper trip","bridging","fill"]
    if any(k in desc_lower for k in h3): return "H³"
    if any(k in desc_lower for k in h2): return "H²"
    if any(k in desc_lower for k in h1): return "H¹"
    return "H⁰"

def gate_check(k_curr, k_prior):
    dl1 = k_curr["lambda_1"] - k_prior["lambda_1"]
    hol  = k_curr["holonomy_signature"]
    l1   = k_curr["lambda_1"]
    if dl1 < -0.5 or hol != "trivial": status = "HALT_A4"
    elif dl1 < -0.1 or l1 < 0.001:    status = "WARN"
    else:                               status = "PASS"
    return dl1, status

def save_ddr(num, rdate, depth_in, depth_out, mw, ecd, ops, plan,
             problems, day_cost, cum_cost, k_s, dl1, a4):
    ddr = {
        "report_number": num, "report_date": rdate, "well_name": WELL,
        "afe_number": AFE_NO, "rig_name": RIG, "operator_rep": SUPT,
        "depth_start_ft": depth_in, "depth_end_ft": depth_out,
        "footage": depth_out - depth_in,
        "mud_weight_ppg": mw, "ecd_ppg": ecd,
        "operations_24hr": ops, "plan_next_24hr": plan,
        "problems": problems,
        "day_cost_usd": day_cost, "cumulative_cost_usd": cum_cost,
        "afe_approved_usd": AFE_AMT,
        "afe_burn_pct": round(cum_cost / AFE_AMT * 100, 1),
        "k_s_snapshot": k_s, "delta_lambda_1": round(dl1, 6),
        "a4_triggered": a4,
    }
    path = EVIDENCE / "ddrs" / f"DDR_{num:04d}_{rdate}.json"
    path.write_text(json.dumps(ddr, indent=2))
    return ddr, path

def harvest_pair(ddr_num, problem_type, desc_problem, desc_solution,
                 ks_p, ks_s, dl1, formation, res_hrs, cost_impact):
    global shape_pair_count
    if dl1 < 0:
        print(f"  [Harvester] NOT captured: Δλ₁={dl1:+.4f} < 0")
        return None
    pair = {
        "pair_id": f"{WELL}-DDR{ddr_num:04d}-{problem_type}",
        "well_name": WELL, "problem_type": problem_type,
        "problem_description": desc_problem, "solution_description": desc_solution,
        "k_s_problem": ks_p, "k_s_solution": ks_s,
        "delta_lambda_1": round(dl1, 6),
        "formation": formation, "resolution_hours": res_hrs,
        "cost_impact_usd": cost_impact,
    }
    with open(PAIRS_FILE, "a") as f:
        f.write(json.dumps(pair) + "\n")
    shape_pair_count += 1
    return pair

# ─────────────────────────────────────────────────────────────────────────────
# MORNING REPORT
# ─────────────────────────────────────────────────────────────────────────────
def morning_report(depth, footage_24, ob_hrs, bit, bit_hrs, mw, ecd,
                   spent, ops, plan, problems, ks):
    depth_pct = depth / TD_FT * 100
    afe_pct   = spent / AFE_AMT * 100
    cost_eff  = (afe_pct / 100) / max(0.001, depth_pct / 100)
    flat_hrs  = 24.0 - ob_hrs
    avg_rop   = footage_24 / max(0.1, ob_hrs)
    rem_ft    = TD_FT - depth
    days_to_td = rem_ft / max(1, footage_24) if footage_24 > 0 else 0

    l1 = ks["lambda_1"]
    hol = ks["holonomy_signature"]
    afe_coh = ks["afe_coherence"]

    if l1 >= 0.10 and hol == "trivial" and afe_coh >= 0.8:
        icon, status = "🟢", "GREEN — DRILLING AHEAD"
    elif l1 >= 0.01 and hol == "trivial":
        icon, status = "🟡", "YELLOW — MONITOR CLOSELY"
    else:
        icon, status = "🔴", "RED — A4 REVIEW REQUIRED"

    report = f"""
{'='*70}
MORNING REPORT — {date.today()}  {icon} {status}
Well: {WELL}   AFE: {AFE_NO}   Rig: {RIG}
{'='*70}

DEPTH STATUS @ 0600
  Current depth:   {depth:>8,.0f} ft  ({depth_pct:.1f}% of TD)
  TD (program):    {TD_FT:>8,.0f} ft
  Footage 24hr:    {footage_24:>8,.0f} ft
  On-bottom hrs:   {ob_hrs:>8.1f} hrs   Flat time: {flat_hrs:.1f} hrs ({flat_hrs/24*100:.0f}%)
  Avg ROP:         {avg_rop:>8.1f} ft/hr
  Remaining to TD: {rem_ft:>8,.0f} ft   (~{days_to_td:.1f} days at current pace)

CURRENT BIT:  {bit}  ({bit_hrs:.1f} hrs on bit)
MUD:  MW {mw:.2f} ppg   ECD {ecd:.2f} ppg   ΔP/ΔV {ecd-mw:+.2f} ppg {'⚠️' if abs(ecd-mw)>0.4 else '✅'}

AFE STATUS
  Approved:     ${AFE_AMT:>12,.0f}
  Spent:        ${spent:>12,.0f}  ({afe_pct:.1f}%)
  Remaining:    ${AFE_AMT-spent:>12,.0f}
  Cost efficiency: {cost_eff:.2f}x  {'⚠️ Over budget for depth' if cost_eff>1.15 else '✅ On track'}

OPERATIONS — LAST 24 HOURS
  {ops}
"""
    if problems:
        report += "ACTIVE PROBLEMS\n"
        for p in problems:
            report += f"  ⚠️  {p}\n"
    report += f"""
PLAN — NEXT 24 HOURS
  {plan}

{'─'*70}
WELLBORE COHERENCE [ZuluYokohama Protocol K(S)]
  dim H⁰ = {ks['dim_H0']}  |  λ₁ = {l1:.4f}  {'✅' if l1>=0.10 else '🟡' if l1>=0.01 else '🔴'}
  Holonomy: {hol}  {'✅' if hol=='trivial' else '🔴 CONTRADICTION — RESOLVE BEFORE ADVANCING'}
  AFE coherence: {afe_coh:.3f}  |  NPT density: {ks['npt_density']:.3f}
{'─'*70}
Prepared by: OG-EP Superintendent System (ZuluYokohama Protocol)
{'='*70}"""
    return report


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DEMO
# ─────────────────────────────────────────────────────────────────────────────
def run():
    print("\n" + "="*70)
    print("  OG-EP SUPERINTENDENT SYSTEM — END-TO-END DEMO")
    print(f"  Well: {WELL}")
    print(f"  AFE: {AFE_NO}  |  Approved: ${AFE_AMT:,.0f}")
    print("="*70)

    today = date.today()

    # ── DAY 1 BASELINE — Intermediate at 5,200ft ─────────────────────────
    sep("DAY 1 — Intermediate 5,200ft (Baseline K(S))")
    ks1 = compute_well_key_lite(
        depth_ft=5200, td_ft=TD_FT, afe_spent=450_000, afe_approved=AFE_AMT,
        mw_ppg=9.4, ecd_ppg=9.6, npt_hours=1.5, total_hours=24,
        n_cased_intervals=2, n_open_intervals=2,
        timestamp=(today - timedelta(days=2)).isoformat(), well_name=WELL,
    )
    print(f"  Baseline K(S):")
    print(f"    dim H⁰ = {ks1['dim_H0']}  |  λ₁ = {ks1['lambda_1']:.4f}")
    print(f"    Holonomy: {ks1['holonomy_signature']}")
    print(f"    AFE coherence: {ks1['afe_coherence']:.3f}  |  NPT: {ks1['npt_density']:.3f}")

    # ── DAY 2 — Normal drilling, 6,150ft ─────────────────────────────────
    sep("DAY 2 — Normal drilling, 6,150ft")
    ks2 = compute_well_key_lite(
        depth_ft=6150, td_ft=TD_FT, afe_spent=580_000, afe_approved=AFE_AMT,
        mw_ppg=9.4, ecd_ppg=9.7, npt_hours=4.0, total_hours=24,
        n_cased_intervals=2, n_open_intervals=2,
        timestamp=(today - timedelta(days=1)).isoformat(), well_name=WELL,
    )
    dl1_d2, gate_d2 = gate_check(ks2, ks1)
    print(f"  K(S):  λ₁={ks2['lambda_1']:.4f}  Δλ₁={dl1_d2:+.4f}  {gate_label(gate_d2)}")
    print(f"  Holonomy: {ks2['holonomy_signature']}")

    h_class2 = h_route("tight hole reaming 3 stands")
    print(f"  Event class: {h_class2} → LOCAL handling")

    _, ddr2_path = save_ddr(
        num=12, rdate=(today-timedelta(days=1)).isoformat(),
        depth_in=5200, depth_out=6150,
        mw=9.4, ecd=9.7,
        ops="Drilled 8-1/2\" from 5,200ft to 6,150ft (950ft). Tight hole at 5,840ft — reamed 3 stands. 4hrs NPT.",
        plan="Continue to 7,500ft. Wiper trip at 7,000ft per program.",
        problems=["Tight hole 5,840ft — resolved, not recurring"],
        day_cost=128_000, cum_cost=580_000,
        k_s=ks2, dl1=dl1_d2, a4=(gate_d2=="HALT_A4"),
    )
    print(f"  ✅ DDR #12 saved → {ddr2_path.name}")

    # ── DAY 3 — TROUBLE: Packoff at 7,240ft ──────────────────────────────
    sep("DAY 3 — TROUBLE: Packoff / Stuck at 7,240ft")
    ks3 = compute_well_key_lite(
        depth_ft=7240, td_ft=TD_FT, afe_spent=740_000, afe_approved=AFE_AMT,
        mw_ppg=9.5, ecd_ppg=10.1, npt_hours=14.0, total_hours=24,
        n_cased_intervals=2, n_open_intervals=2,
        is_holonomy_diverged=True,  # ECD vs MW diverged
        timestamp=(today - timedelta(days=0, hours=12)).isoformat(), well_name=WELL,
    )
    dl1_d3, gate_d3 = gate_check(ks3, ks2)
    print(f"  K(S):  λ₁={ks3['lambda_1']:.4f}  Δλ₁={dl1_d3:+.4f}  {gate_label(gate_d3)}")
    print(f"  Holonomy: {ks3['holonomy_signature']}")

    h_class3 = h_route("packoff severe overpull 18 tons stuck pipe")
    print(f"  Event class: {h_class3}")

    # Routing decision
    print()
    print("  ROUTING DECISION:")
    if h_class3 == "H²":
        print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  ROUTE:    REMOTE — H² SYSTEMIC OBSTRUCTION")
        print("  TIME:     URGENT")
        print("  ACTION:   Escalate to drilling engineer.")
        print("            Do NOT attempt local patch. Halt downhole operations.")
        print("            Prepare full K(S) package for engineering review.")
        print(f"  NOTIFY:   → Drilling Engineer: {'+1 307-555-0142'}")
        print(f"            → Rig Manager: Dave Kowalski +1 307-555-0199")
        print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        print(f"  ROUTE: LOCAL — {h_class3}")
        print(f"  ACTION: Apply local corrective action. Monitor Δλ₁ every 6hrs.")

    _, ddr3_path = save_ddr(
        num=13, rdate=today.isoformat(),
        depth_in=6150, depth_out=7240,
        mw=9.5, ecd=10.1,
        ops="Drilled to 7,240ft. Packoff encountered — pumps up on connections. 18 tons overpull. Work string operation initiated at 1630.",
        plan="Work free. Spot LCM pill (20ppb mica/walnut). POOH wiper trip. Resume drilling.",
        problems=["PACKOFF 7,240ft — 18t overpull, ECD 10.1ppg (MW 9.5ppg)", "14hrs NPT"],
        day_cost=168_000, cum_cost=740_000,
        k_s=ks3, dl1=dl1_d3, a4=True,
    )
    print(f"\n  🔴 A4 TRIGGERED — DDR #13 saved → {ddr3_path.name}")

    # ── DAY 4 — Resolution ────────────────────────────────────────────────
    sep("DAY 4 — RESOLVED: Back to drilling, 7,480ft")
    ks4 = compute_well_key_lite(
        depth_ft=7480, td_ft=TD_FT, afe_spent=870_000, afe_approved=AFE_AMT,
        mw_ppg=9.6, ecd_ppg=9.8, npt_hours=2.0, total_hours=24,
        n_cased_intervals=2, n_open_intervals=2,
        is_holonomy_diverged=False,
        timestamp=today.isoformat(), well_name=WELL,
    )
    dl1_d4, gate_d4 = gate_check(ks4, ks3)
    print(f"  K(S):  λ₁={ks4['lambda_1']:.4f}  Δλ₁={dl1_d4:+.4f}  {gate_label(gate_d4)}")
    print(f"  Holonomy: {ks4['holonomy_signature']}")

    # Harvest shape pair
    pair = harvest_pair(
        ddr_num=14,
        problem_type="packoff_stuck_pipe",
        desc_problem="Packoff at 7,240ft in Carlile shale. 18 tons overpull. ECD spike 10.1ppg.",
        desc_solution="Worked free with 6hr rotation/recip. LCM pill (20ppb mica/walnut) resolved losses. Back to drilling.",
        ks_p=ks3, ks_s=ks4, dl1=dl1_d4,
        formation="Carlile Shale", res_hrs=18.0, cost_impact=45_000,
    )
    if pair:
        print(f"  ✅ Shape pair HARVESTED → shape_pairs.jsonl")
        print(f"     problem→solution Δλ₁ = {dl1_d4:+.4f}")

    _, ddr4_path = save_ddr(
        num=14, rdate=(today + timedelta(days=1)).isoformat(),
        depth_in=7240, depth_out=7480,
        mw=9.6, ecd=9.8,
        ops="Worked free at 0430. LCM pill pumped. POOH 6,500ft wiper, back to bottom. Resumed drilling to 7,480ft (240ft).",
        plan="Drill to 8,000ft (9-5/8\" casing shoe). Pre-flush seat. Rig up to run casing.",
        problems=[],
        day_cost=152_000, cum_cost=870_000,
        k_s=ks4, dl1=dl1_d4, a4=False,
    )
    print(f"  ✅ DDR #14 saved → {ddr4_path.name}")

    # ── MORNING REPORT ────────────────────────────────────────────────────
    sep("MORNING REPORT — Generated at 0600")
    report = morning_report(
        depth=7480, footage_24=240, ob_hrs=10,
        bit='8-1/2" PDC 6-blade (S/N PDC-2024-441)', bit_hrs=96.0,
        mw=9.6, ecd=9.8,
        spent=870_000,
        ops="Resolved packoff. LCM pill. Wiper trip. Back to drilling. 240ft in 10hr on-bottom.",
        plan="Drill to 8,000ft casing shoe. Rig up 9-5/8\" string. Cement.",
        problems=["Monitor ECD in remaining Carlile shale — tight above 7,500ft"],
        ks=ks4,
    )
    print(report)

    # ── AFE STATUS ────────────────────────────────────────────────────────
    sep("AFE COHERENCE CHECK")
    # Simple variance analysis (no scipy needed)
    line_items = [
        ("100", "Rig Day Rate",           950_000, 320_000, 490_000),
        ("200", "Directional / MWD",      280_000,  95_000, 165_000),
        ("210", "Drilling Bits",            85_000,  42_000,  35_000),
        ("220", "Drilling Fluids",         180_000,  78_000,  95_000),
        ("230", "Mud Logging",              65_000,  22_000,  38_000),
        ("300", "Casing & Tubing",         420_000,  38_000, 390_000),
        ("320", "Cementing",               140_000,  12_000, 135_000),
        ("310", "Wellhead & BOP",           85_000,  82_000,   2_000),
        ("500", "Fuel & Water",             65_000,  30_000,  32_000),
        ("700", "Contingency",             130_000,       0,  45_000),
    ]
    total_appr = sum(x[2] for x in line_items)
    total_actl = sum(x[3] for x in line_items)
    total_fcst = sum(x[3]+x[4] for x in line_items)
    total_var  = total_fcst - total_appr
    var_pct    = total_var / total_appr * 100

    print(f"\n  {'CODE':<6} {'DESCRIPTION':<28} {'APPROVED':>10} {'ACTUAL':>10} {'FORECAST':>10} {'VAR%':>7}")
    print("  " + "─" * 72)
    over_budget = []
    for code, desc, appr, actl, ftc in line_items:
        fcst = actl + ftc
        vp = (fcst - appr) / appr * 100
        flag = "⚠️" if vp > 10 else ""
        print(f"  {code:<6} {desc:<28} ${appr:>9,.0f} ${actl:>9,.0f} ${fcst:>9,.0f} {vp:>+6.1f}% {flag}")
        if vp > 10:
            over_budget.append((code, desc, vp, fcst-appr))
    print("  " + "─" * 72)
    print(f"  {'TOTAL':<34} ${total_appr:>9,.0f} ${total_actl:>9,.0f} ${total_fcst:>9,.0f} {var_pct:>+6.1f}%")

    gate_afe = "HALT_A4" if var_pct > 25 else "WARN" if var_pct > 10 else "PASS"
    print(f"\n  AFE Gate: {gate_label(gate_afe)}")
    if gate_afe != "PASS":
        print(f"  Over-budget line items ({len(over_budget)}):")
        for code, desc, vp, extra in over_budget:
            print(f"    → {code} {desc}: {vp:+.1f}% (${extra:+,.0f})")
    if gate_afe == "HALT_A4":
        print("\n  ⚠️  AFE SUPPLEMENT REQUIRED before next PO approval.")
        print("     System auto-drafting supplement — superintendent review needed.")

    # ── SUMMARY ──────────────────────────────────────────────────────────
    sep("EVIDENCE LEDGER SUMMARY")
    ddr_files = list((EVIDENCE / "ddrs").glob("*.json"))
    print(f"\n  {'Well:':<22} {WELL}")
    print(f"  {'DDRs saved:':<22} {len(ddr_files)}")
    print(f"  {'Shape pairs harvested:':<22} {shape_pair_count}")
    print(f"  {'Final K(S) λ₁:':<22} {ks4['lambda_1']:.4f}")
    print(f"  {'Final holonomy:':<22} {ks4['holonomy_signature']}")
    print(f"  {'AFE gate status:':<22} {gate_afe}")
    print(f"  {'AFE spent/approved:':<22} ${870_000:,.0f} / ${AFE_AMT:,.0f} ({870_000/AFE_AMT*100:.1f}%)")
    print(f"  {'Depth / TD:':<22} 7,480 / {TD_FT:,.0f} ft ({7480/TD_FT*100:.1f}%)")
    print()
    print("  Evidence files:")
    for f in sorted(ddr_files):
        print(f"    {f.name}")
    if PAIRS_FILE.exists():
        print(f"    {PAIRS_FILE.name}  ({shape_pair_count} pairs)")
    print()
    print("  ── The mathematics are the operating system.")
    print("  ── The Anvil holds at the rig floor.")
    print("=" * 70)


if __name__ == "__main__":
    run()
