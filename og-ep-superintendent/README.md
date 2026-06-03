# OG-EP Superintendent System

**Modern O&G E&P operations platform for an old-school superintendent — new startup.**

Built on [ZuluYokohama Protocol](https://github.com/ZuluYokohama/zulu-yokohama-protocol) mathematics.
Replaces Book1.xlsx with a topological runtime.

---

## What It Does

Replaces the superintendent's Excel workbook with a live topological system:

| Was Excel | Now |
|---|---|
| DDR sheet | `core/ddr_harvester.py` — auto DDR + K(S) evidence bundle |
| AFE tracking | `core/afe_laplacian.py` — cost coherence + auto supplement draft |
| Morning report | `ui/morning_report.py` — 0600 auto-generate |
| NPT log | A4 gate — triggered on Δλ₁ < 0 or non-trivial holonomy |
| Bit record | Shape pairs → `evidence/shape_pairs.jsonl` |
| Well program | `data/well_program.py` — term series with Δλ₁ gate between phases |

## The Protocol Mapping

| ZuluYokohama Concept | O&G Field Reality |
|---|---|
| **K(S)** = (dim H⁰, λ₁, holonomy) | Well fingerprint — is the wellbore coherent? |
| **Δλ₁ ≥ 0** | Positive progress — making hole, solving problems |
| **Δλ₁ < 0 → A4 HALT** | NPT event, over-AFE, stuck pipe → stop and review |
| **LOCAL route** | Superintendent handles it at the rig floor |
| **REMOTE route** | Escalate to drilling engineer |
| **H³ violation** | Well control — BOP, NOW |
| **Shape pairs** | K(S)_problem ↔ K(S)_solution — training data for local formation AI |
| **GeometryHarvester** | DDR harvester — captures every resolved problem |
| **Term series** | Spud → Surface → Intermediate → Production → TD |

## Quick Start

```bash
# Zero dependencies — runs on any Python 3.8+
python3 run_demo_lite.py
```

Requires scipy + numpy for full engine:
```bash
pip install scipy numpy
python3 full_demo.py
```

## Structure

```
og-ep-superintendent/
├── SUPERINTENDENT_SYSTEM_MANIFEST.md   # Full architecture
├── core/
│   ├── wellbore_topology.py            # Sheaf Laplacian K(S) engine
│   ├── afe_laplacian.py                # AFE cost topology
│   ├── ddr_harvester.py                # DDR saves + shape pair capture
│   └── topology_lite.py               # Zero-dep fallback (ARM64/field tablet)
├── router/
│   └── ops_bipartite_router.py         # LOCAL / REMOTE / WELL CONTROL routing
├── ui/
│   └── morning_report.py               # 0600 morning report generator
├── data/
│   └── well_program.py                 # Well program as configurational term series
├── evidence/                           # DDRs, AFE snapshots, shape pairs
└── docs/
    └── SUPERINTENDENT_GUIDE.md         # Plain-language field guide
```

## Evidence (Live Demo Output)

- 3 DDRs from `Blackstone Federal 1-28H` (Nabors 453, Campbell County WY)
- Day 3: A4 triggered — packoff at 7,240ft, non-trivial holonomy (`ecd-mw-divergence-0.60ppg`)
- Day 4: Δλ₁ = **+0.7259** after resolution — shape pair harvested
- AFE gate: PASS at 30.5% spent / 65% depth

---

*The mathematics are the operating system. The Anvil holds at the rig floor.*

**ZuluYokohama Protocol — Applied to O&G E&P**
