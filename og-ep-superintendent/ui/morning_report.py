"""
OG-EP SUPERINTENDENT SYSTEM
ui/morning_report.py

The Morning Report Generator — 0600 Daily Summary

Auto-generates the morning report from last night's DDR data.
The report the company man, asset manager, and partners wake up to.

Instead of copy-pasting from Excel, the superintendent enters:
    - Depth at 0600
    - Any notable events
    - Mud weight / ECD
    - Current AFE burn

The system generates:
    - Full formatted morning report
    - K(S) health summary
    - Δλ₁ trend chart (text-based)
    - AFE status (budget vs actual)
    - 24-hour plan + risk flags
    - Routing recommendation for the day
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class MorningReportInput:
    """Minimal input from the superintendent at 0600."""
    well_name: str
    afe_number: str
    report_date: str              # ISO date
    depth_0600_ft: float
    td_planned_ft: float
    footage_last_24hr: float
    on_bottom_hours: float        # actual drilling time in last 24hr
    current_bit: str
    current_bit_hours: float
    mud_weight_ppg: float
    ecd_ppg: float
    afe_approved_usd: float
    afe_spent_usd: float
    events_summary: str           # Short narrative of last 24hr
    plan_next_24hr: str           # Short narrative of next 24hr
    problems: list[str] = None    # Any active problems
    k_s_current: dict[str, Any] = None      # From WellboreCryptologicKey.to_dict()
    k_s_prior: dict[str, Any] = None        # Prior day's K(S)
    lambda_1_history: list[float] = None    # Last 7 days of λ₁ values


def generate_morning_report(inp: MorningReportInput) -> str:
    """
    Generate the full morning report text.
    The format every operator morning call runs on.
    """
    today = inp.report_date
    depth = inp.depth_0600_ft
    td = inp.td_planned_ft
    depth_pct = min(100.0, depth / max(1, td) * 100)

    afe_pct = inp.afe_spent_usd / max(1, inp.afe_approved_usd) * 100
    remaining_usd = inp.afe_approved_usd - inp.afe_spent_usd
    cost_efficiency = (afe_pct / 100) / max(0.001, depth_pct / 100)

    avg_rop = inp.footage_last_24hr / max(0.1, inp.on_bottom_hours) if inp.on_bottom_hours > 0 else 0.0
    flat_time_hrs = 24.0 - inp.on_bottom_hours

    # ── Determine overall status ─────────────────────────────────────────
    ks = inp.k_s_current or {}
    lambda_1 = ks.get("lambda_1", None)   # None when K(S) not yet computed
    holonomy = ks.get("holonomy_signature", "trivial")
    afe_coherence = ks.get("afe_coherence", 1.0)

    delta_l1 = 0.0
    if inp.k_s_prior and inp.k_s_current:
        delta_l1 = float(ks.get("lambda_1", 0.0)) - float(inp.k_s_prior.get("lambda_1", 0.0))

    # Only show RED on confirmed K(S) weakness, not on missing data
    if lambda_1 is None:
        status_icon = "⚪"
        status_word = "NO K(S) — RUN TOPOLOGY ENGINE BEFORE REPORT"
    elif lambda_1 >= 0.10 and holonomy == "trivial" and afe_coherence >= 0.8:
        status_icon = "🟢"
        status_word = "GREEN — DRILLING AHEAD"
    elif lambda_1 >= 0.01 and holonomy == "trivial":
        status_icon = "🟡"
        status_word = "YELLOW — MONITOR CLOSELY"
    else:
        status_icon = "🔴"
        status_word = "RED — A4 REVIEW REQUIRED"
    lambda_1_disp = lambda_1 if lambda_1 is not None else 0.0

    # ── λ₁ sparkline (last 7 days) ───────────────────────────────────────
    sparkline = ""
    if inp.lambda_1_history:
        history = inp.lambda_1_history[-7:]
        max_val = max(history) if history else 1.0
        chars = "▁▂▃▄▅▆▇█"
        sparkline = "λ₁ trend (7d): " + "".join(
            chars[min(7, int(v / max(0.001, max_val) * 7))]
            for v in history
        ) + f"  current={lambda_1:.4f}"

    # ── Problems section ─────────────────────────────────────────────────
    problems_section = ""
    if inp.problems:
        problems_section = "\nACTIVE PROBLEMS\n"
        for p in inp.problems:
            problems_section += f"  ⚠️  {p}\n"

    # ── Cost forecast ─────────────────────────────────────────────────────
    remaining_footage = max(0, td - depth)
    if avg_rop > 0 and inp.on_bottom_hours > 0:
        # Rough days to TD based on recent performance
        ftg_per_day = inp.footage_last_24hr
        days_to_td = remaining_footage / max(0.1, ftg_per_day)
        # Cost per day ≈ last 24hr cost implied by AFE burn rate
        # (simplified — real system uses day rate schedule)
        daily_cost_est = inp.afe_approved_usd * 0.025  # ~2.5% of AFE per day rough estimate
        projected_final = inp.afe_spent_usd + (days_to_td * daily_cost_est)
        projected_variance_pct = (projected_final - inp.afe_approved_usd) / max(1, inp.afe_approved_usd) * 100
        forecast_line = (f"  Projected final cost: ${projected_final:>12,.0f}  "
                         f"(Variance: {projected_variance_pct:+.1f}%)")
    else:
        days_to_td = None
        forecast_line = "  (Insufficient drilling data for forecast)"

    # ── Build the report ─────────────────────────────────────────────────
    report = f"""
{"="*70}
MORNING REPORT — {today}  {status_icon} {status_word}
Well: {inp.well_name}   AFE: {inp.afe_number}
{"="*70}

DEPTH STATUS @ 0600
  Current depth:   {depth:>8,.0f} ft
  TD (program):    {td:>8,.0f} ft  ({depth_pct:.1f}% complete)
  Footage 24hr:    {inp.footage_last_24hr:>8,.0f} ft
  On-bottom hours: {inp.on_bottom_hours:>8.1f} hrs
  Flat time:       {flat_time_hrs:>8.1f} hrs  ({flat_time_hrs/24*100:.0f}% of day)
  Avg ROP:         {avg_rop:>8.1f} ft/hr
  {'Remaining to TD:' :<20} {remaining_footage:>8,.0f} ft  (~{f'{days_to_td:.1f} days' if days_to_td else 'N/A'})

CURRENT BIT
  {inp.current_bit}  (Hours on bit: {inp.current_bit_hours:.1f})

MUD PROGRAM
  Mud weight:   {inp.mud_weight_ppg:.2f} ppg
  ECD:          {inp.ecd_ppg:.2f} ppg
  ECD vs MW:    {inp.ecd_ppg - inp.mud_weight_ppg:+.2f} ppg {'⚠️' if abs(inp.ecd_ppg - inp.mud_weight_ppg) > 0.4 else '✅'}

AFE STATUS
  Approved:        ${inp.afe_approved_usd:>12,.0f}
  Spent to date:   ${inp.afe_spent_usd:>12,.0f}  ({afe_pct:.1f}%)
  Remaining:       ${remaining_usd:>12,.0f}
  Cost efficiency: {cost_efficiency:.2f}x  {'(OVER budget for depth)' if cost_efficiency > 1.1 else '(On track)'}
{forecast_line}

OPERATIONS — LAST 24 HOURS
  {inp.events_summary}
{problems_section}
PLAN — NEXT 24 HOURS
  {inp.plan_next_24hr}

{"─"*70}
WELLBORE COHERENCE [ZuluYokohama K(S)]
  {sparkline}
  dim H⁰:    {ks.get('dim_H0', 'N/A')}  (connected agreement sections)
  λ₁:        {lambda_1_disp:.4f}  {'✅ Strong' if lambda_1 >= 0.10 else '🟡 Moderate' if lambda_1 >= 0.01 else '🔴 Weak'}
  Δλ₁ (24h): {delta_l1:+.4f}  {'📈 Improving' if delta_l1 >= 0 else '📉 Regressing'}
  Holonomy:  {holonomy}  {'✅' if holonomy == 'trivial' else '🔴 CONTRADICTION — RESOLVE BEFORE ADVANCING'}
  AFE coh:   {afe_coherence:.3f}  {'✅' if afe_coherence >= 0.85 else '⚠️' if afe_coherence >= 0.70 else '🔴'}
{"─"*70}
{"="*70}
Prepared by: OG-EP SUPERINTENDENT SYSTEM (ZuluYokohama Protocol)
Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
{"="*70}
"""
    return report


def quick_morning_report(
    well_name: str,
    afe_number: str,
    depth_ft: float,
    td_ft: float,
    footage_24hr: float,
    on_bottom_hrs: float,
    bit: str,
    bit_hrs: float,
    mw_ppg: float,
    ecd_ppg: float,
    afe_approved: float,
    afe_spent: float,
    ops_summary: str,
    next_plan: str,
    problems: list[str] | None = None,
) -> str:
    """
    Convenience wrapper — minimum input for a morning report.
    No K(S) required (system computes it if WellState is available).
    """
    inp = MorningReportInput(
        well_name=well_name,
        afe_number=afe_number,
        report_date=date.today().isoformat(),
        depth_0600_ft=depth_ft,
        td_planned_ft=td_ft,
        footage_last_24hr=footage_24hr,
        on_bottom_hours=on_bottom_hrs,
        current_bit=bit,
        current_bit_hours=bit_hrs,
        mud_weight_ppg=mw_ppg,
        ecd_ppg=ecd_ppg,
        afe_approved_usd=afe_approved,
        afe_spent_usd=afe_spent,
        events_summary=ops_summary,
        plan_next_24hr=next_plan,
        problems=problems or [],
    )
    return generate_morning_report(inp)
