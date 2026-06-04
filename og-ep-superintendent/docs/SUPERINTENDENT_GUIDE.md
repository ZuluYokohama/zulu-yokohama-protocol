# OG-EP SUPERINTENDENT GUIDE
## Field Guide for an Old-School Superintendent
### No Math Required — Just Drilling

---

## What This System Does

You already know how to drill a well. You've been doing it for 20 years.
The problem is the **paperwork** — the DDR, the AFE tracking, the morning report,
the bit record, the NPT log. That's what eats your evenings.

This system handles all of it. You enter the data once. It spits out:
- Morning report (formatted, ready to email by 0600)
- DDR (complete, with your narrative)
- AFE status (green/yellow/red — just like a traffic light)
- Bit advisory (when to pull based on your own formation data)
- Problem routing (who to call and what to tell them)

---

## The Traffic Light

The system gives every wellbore situation one of four levels:

| Color | Level | Means | What You Do |
|-------|-------|-------|-------------|
| ✅ Green | H⁰ | Normal ops | Drill ahead |
| 🟡 Yellow | H¹ | Local problem | Fix it yourself, monitor |
| 🔴 Red | H² | Systemic | Call the drilling engineer |
| ⚫ Black | H³ | Well control | BOP. NOW. |

This is just the old-school H-classification system you already know.
The difference is the system detects it automatically from the data
instead of waiting for you to see it.

---

## Daily Workflow

### Every Tour (12hr)
```
1. Check depth. Enter in system.
2. Any problems? Enter them.
3. System tells you: GREEN / YELLOW / RED
4. If GREEN → drill ahead
5. If YELLOW → fix locally, re-check in 6hr
6. If RED → system gives you the call list and what to say
```

### Morning Report (0600)
```
1. Enter: depth, footage, mud weight, ECD
2. Write 2-line ops summary
3. Write 2-line next 24hr plan
4. System generates the full formatted report
5. Copy → email → done in 5 minutes
```

### DDR (End of Day)
```
1. Fill in the DDR form (depth, hours, parameters)
2. Add any problems and what you did about them
3. System writes the full DDR with K(S) snapshot
4. Saves automatically to the evidence folder
```

### AFE Check (Weekly or on any cost surprise)
```
1. Update actual costs by cost code
2. System shows you: which lines are over, by how much
3. RED AFE → system auto-drafts the supplement
4. You review numbers, sign, send to management
```

---

## The K(S) Number — What It Means

The system tracks a number called **λ₁** (lambda-one).
Think of it as the well's **coherence score**.

- **λ₁ high (> 0.10)** → Everything agrees. Plan matches actual. Drill ahead.
- **λ₁ medium (0.01–0.10)** → Some disagreement. Watch it.
- **λ₁ low (< 0.01)** → Something is off. Figure out what before advancing.

**Δλ₁** is the change from the last DDR:
- **Δλ₁ positive** → Getting better (making hole, solving problems)
- **Δλ₁ negative** → Getting worse (NPT accumulating, costs diverging)

If Δλ₁ goes below -0.5, the system flags it as **A4** — that's the "stop and review" signal.
Same as an OMEGA-CLASS HALT in the protocol. In field terms: don't go deeper until you know why.

---

## The Shape Pairs — Your Well's Memory

Every time you have a problem and fix it, the system saves a **shape pair**:
```
[What the well looked like when the problem started]
    ↕
[What the well looked like after you fixed it]
```

Over time, these pairs train the local AI model on YOUR formation.
The Frontier Sands on your lease are not the Frontier Sands on someone else's.
After 3–5 wells, the system knows YOUR geology and starts predicting problems
before they happen.

This is the **distillation feedback loop** from the protocol —
applied to your bit runs instead of code changes.

---

## Common Scenarios

### Tight Hole / Overpull
```
System sees: ECD spike + low ROP + NPT hours increasing
→ Classifies: H¹ (local fixable)
→ Routing: LOCAL — "Ream out, monitor Δλ₁ every 6hrs. If no improvement → escalate."
→ Shape pair captured after wiper trip resolves it
```

### Lost Circulation
```
System sees: Mud weight vs. ECD divergence > 0.5ppg (holonomy non-trivial)
→ Classifies: H² (systemic)
→ Routing: REMOTE — "Call drilling engineer. LCM pill or casing required."
→ AFE supplement auto-drafted for lost circulation material cost
```

### Over-AFE
```
System sees: AFE burn rate > depth fraction by 30%
→ Holonomy: "non-trivial:afe-overrun-1.30x"
→ Routing: REMOTE — "File AFE supplement before next PO approval"
→ Draft supplement generated, shows which cost codes are overrunning
```

### Well Control
```
System sees: Any kick / flow check / shut-in mention in event log
→ Classifies: H³
→ Response: Full well control protocol printed immediately
→ No routing delay — immediate action
```

---

## What Goes in the Evidence Folder

```
evidence/
├── shape_pairs.jsonl          ← Every resolved problem (training data)
├── ddrs/
│   └── Blackstone_Federal_1-28H/
│       ├── DDR_0001_2026-06-01.json
│       ├── DDR_0002_2026-06-02.json
│       └── ...
└── afe_snapshots/
    └── 2026-FEP-001/
        ├── AFE_snapshot_2026-06-01.json
        └── ...
```

This is your **as-built record**. Better than any handwritten logbook.
Every K(S) number is there. Every A4 event is documented with before/after.
When the post-well audit comes — everything is already in there.

---

## Starting a New Well

```python
from data.well_program import build_standard_vertical_program

program = build_standard_vertical_program(
    well_name      = "Your Well 1-XX",
    api_number     = "XX-XXX-XXXXX-00-00",
    operator       = "Your Company",
    afe_number     = "2026-XXX-001",
    afe_approved_usd = 2_500_000,
    td_planned_ft  = 11000,
    surface_casing_depth_ft = 1800,
    intermediate_casing_depth_ft = 7500,
    field_name     = "Your Field",
    county_state   = "Your County, ST",
)
print(program.format_program_summary())
```

Adjust the casing seats, AFE amounts, and formation prognosis to match your program.
The system does the rest.

---

## The Rig Tablet

The full system runs on a ruggedized Android tablet at the doghouse.
No internet required. All AI runs locally (6GB model, ARM processor).
The tablet syncs to the office server when the satellite uplink is active.

The superintendent talks to it like he talks to the mudlogger:
- "What's the ECD doing?"
- "When should I pull this bit?"
- "How much AFE do I have left?"
- "Write me a morning report."

Plain English. No training required.

---

## One Rule

**Never bypass the gate without a written reason in the evidence bundle.**

If the system says A4 and you want to drill ahead anyway —
fine, you're the superintendent, it's your call.
But the system requires you to enter:
1. Why you're bypassing
2. What your contingency is
3. Who authorized it

That gets saved to the evidence bundle automatically.
No judgment. Just documentation.

---

*The mathematics are the operating system. The Anvil holds on the rig floor.*

**ZuluYokohama Protocol — Applied to O&G E&P**
