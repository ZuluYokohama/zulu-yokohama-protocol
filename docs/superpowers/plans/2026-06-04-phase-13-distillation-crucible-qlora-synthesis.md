# Phase 13: The Distillation Crucible & QLoRA Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**I'm using the writing-plans skill to create this implementation plan.**

**Goal:** Build the end-to-end demonstration of the Omega Feedback Loop (`e2e/full_feedback_loop_demo.py`) and a production-constrained QLoRA fine-tuning stub (`distillation/qlora_geometric_tuner.py`) that can consume the growing `datasets/shape_pairs.jsonl` ledger while strictly respecting the 6GB ARM64 UMA + NPU envelope.

**Architecture:** 
- The E2E demo orchestrates the existing Bipartite Router + GeometryHarvester + simulated Remote Oracle to prove the closed feedback loop end-to-end.
- The QLoRA tuner is a heavily constrained PEFT script: 4-bit base model (`Q4_K_M`), low-rank adapters (`r=8`) only on attention/projection layers, loss weighted by the captured `delta_lambda_1` from each Shape Pair, with aggressive memory budgeting for the 6GB UMA ceiling.

**Tech Stack:**
- Existing clean seed components (`bipartite-router-plugin/`, `edge_compute/`, `distillation/geometry_harvester.py`)
- `transformers` + `peft` + `bitsandbytes` (4-bit) + `trl` for the tuner (or `unsloth` if available for speed on edge)
- `llama-cpp-python` or GGUF for the base model loading in the constrained environment
- Strict adherence to WORMHOLE-PATH1 manifests on all new artifacts

**Existing Patterns to Follow:**
- Every new file starts with a full WORMHOLE-PATH1 | OMEGA-CLASS manifest citing relevant axioms (MaxOp Hardware, Phase 3 sparsity, Wormhole-Path 2 distillation, etc.).
- All new code lives under `distillation/` or `e2e/`.
- Integration must go through the existing `BipartiteRouter` and `GeometryHarvester`.
- Evidence bundles are the source of truth.

---

## File Structure Map (Locked)

**New Files:**
- `prime-crystal-grok/e2e/full_feedback_loop_demo.py`
- `prime-crystal-grok/distillation/qlora_geometric_tuner.py`
- `prime-crystal-grok/distillation/__init__.py` (if missing)
- `prime-crystal-grok/docs/EDGE_DISTILLATION_NOTES.md` (optional but recommended)

**Modifications:**
- `prime-crystal-grok/SEED_MANIFEST.md` (record Phase 13)
- Possibly light wiring updates in `bipartite-router-plugin/router_gateway.py` or `distillation/geometry_harvester.py` if the demo reveals small gaps.

**Tests & Verification:**
- The demo itself serves as the executable verification.
- Final evidence bundle: `evidence/e2e/PHASE_13_DISTILLATION_CRUCIBLE_RESULT.json`

---

### Task 1: Project Hygiene & Namespace Preparation

**Files:**
- Modify: `prime-crystal-grok/distillation/__init__.py` (ensure manifest)
- Modify: `prime-crystal-grok/SEED_MANIFEST.md`

- [ ] **Step 1.1: Ensure distillation namespace has proper Phase 11/13 manifest**

Read current `distillation/__init__.py` (if it exists) and ensure it carries a WORMHOLE-PATH1 header referencing Wormhole-Path 2 and the new QLoRA synthesis work.

- [ ] **Step 1.2: Add Phase 13 section to SEED_MANIFEST.md**

Insert a new top-level section after the Wormhole-Path 2 entry:

```markdown
## Phase 13: The Distillation Crucible & QLoRA Synthesis (In Progress)

**Status:** See `docs/superpowers/plans/2026-06-04-phase-13-distillation-crucible-qlora-synthesis.md`

**Target:** End-to-end demonstration of the Omega Feedback Loop + production-constrained QLoRA tuner that respects the 6GB ARM64 UMA envelope.
```

- [ ] **Step 1.3: Commit**

```bash
git add distillation/__init__.py SEED_MANIFEST.md
git commit -m "chore(distillation): prepare Phase 13 Distillation Crucible & QLoRA Synthesis namespace"
```

---

### Task 2: The End-to-End Feedback Loop Demo (`e2e/full_feedback_loop_demo.py`)

**Files:**
- Create: `prime-crystal-grok/e2e/full_feedback_loop_demo.py` (full WORMHOLE-PATH1 manifest required)

- [ ] **Step 2.1: Write the failing skeleton test / demo structure**

Create the file with the full manifest header + a `main()` that prints the planned flow but raises `NotImplementedError` on the critical steps.

Run it to see the red state.

- [ ] **Step 2.2: Implement Turn 1 – Local Analysis Path (using existing BipartiteRouter)**

Use the already-delivered `BipartiteRouter` + `PromptTopology` scanner to show a "safe local" prompt being routed correctly.

- [ ] **Step 2.3: Implement Turn 2 – Remote Path Trigger + Simulated Oracle**

Force an H²-obstruction prompt that routes REMOTE. Simulate the Claude Code Oracle returning an agent-optimized fix that improves coherence.

- [ ] **Step 2.4: Implement the Harvester Capture**

After the simulated successful remote fix, explicitly call the `GeometryHarvester.capture_shape_pair(...)` (or go through the integration layer) and prove the Shape Pair is appended to `datasets/shape_pairs.jsonl`.

- [ ] **Step 2.5: Run the full demo end-to-end and verify the ledger**

Run: `python e2e/full_feedback_loop_demo.py`

Expected: Clean execution, one Shape Pair written, final summary printed, no crashes, and the ledger file updated.

- [ ] **Step 2.6: Commit**

```bash
git add e2e/full_feedback_loop_demo.py datasets/shape_pairs.jsonl
git commit -m "feat(distillation): add full_feedback_loop_demo.py proving the complete Wormhole-Path 2 Omega Feedback Loop"
```

---

### Task 3: The UMA-Bounded QLoRA Geometric Tuner (`distillation/qlora_geometric_tuner.py`)

**Files:**
- Create: `prime-crystal-grok/distillation/qlora_geometric_tuner.py` (full manifest required)

- [ ] **Step 3.1: Write the failing skeleton + argument parser**

Create the file with manifest + a `main()` that parses `--dataset`, `--model`, `--output-dir`, etc., but raises `NotImplementedError` on the actual training.

- [ ] **Step 3.2: Implement strict 4-bit base model loading**

Use `transformers` + `bitsandbytes` (or `unsloth` if available) to load the base model in `load_in_4bit=True` (Q4_K_M equivalent) with `device_map="auto"`.

- [ ] **Step 3.3: Implement low-rank LoRA targeting only attention/projection layers**

Use `peft.LoraConfig` with:
- `r=8`
- `lora_alpha=16`
- `target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (or the equivalent for the chosen base model)
- `lora_dropout=0.05`
- `bias="none"`
- `task_type="CAUSAL_LM"`

- [ ] **Step 3.4: Implement Δλ₁-weighted loss**

Create a custom `compute_loss` (or use a `Trainer` callback) that reads the `delta_lambda_1` field from each training example in the Shape Pair and scales the cross-entropy loss:
`loss = original_loss * (1.0 + max(0, delta_lambda_1) * weight)`

- [ ] **Step 3.5: Add strict memory budgeting + gradient checkpointing + 8-bit optimizers**

Force `gradient_checkpointing=True`, `optim="adamw_8bit"`, `max_grad_norm=0.3`, and any other flags required to stay under ~5.5–5.8 GB during training on the target hardware.

- [ ] **Step 3.6: Add a dry-run / validation mode**

`--dry-run` that loads everything, does a few forward passes on a Shape Pair, reports estimated peak memory, and exits without training.

- [ ] **Step 3.7: Run the dry-run + a tiny real training step on a synthetic 2-example dataset**

- [ ] **Step 3.8: Commit**

```bash
git add distillation/qlora_geometric_tuner.py
git commit -m "feat(distillation): add qlora_geometric_tuner.py — UMA-bounded, Δλ₁-weighted QLoRA fine-tuner for Shape Pairs"
```

---

### Task 4: Packaging, Documentation & Final Verification

- [ ] **Step 4.1:** Ensure `distillation/__init__.py` exports the new tuner cleanly.

- [ ] **Step 4.2:** Create or update `prime-crystal-grok/EDGE_DISTILLATION_NOTES.md` with:
  - How to run the full feedback loop demo
  - How to launch the QLoRA tuner on real hardware (exact command line + expected VRAM)
  - How the resulting adapter can be merged back into the local 8B GGUF for inference

- [ ] **Step 4.3:** Run the full `e2e/repository_audit.py` (or a new edge-specific audit) and confirm zero new pollution introduced by Phase 13 artifacts.

- [ ] **Step 4.4:** Generate the final evidence bundle for the phase:
  - Run both the feedback loop demo and the QLoRA dry-run.
  - Capture output + the resulting (tiny) adapter + updated ledger.
  - Write `evidence/e2e/PHASE_13_DISTILLATION_CRUCIBLE_RESULT.json`

- [ ] **Step 4.5:** Update `SEED_MANIFEST.md` with final Phase 13 status and link to this plan + the evidence bundle.

- [ ] **Step 4.6:** Final commit

```bash
git add distillation/ e2e/ EDGE_DISTILLATION_NOTES.md SEED_MANIFEST.md evidence/e2e/PHASE_13_*.json
git commit -m "feat(distillation): complete Phase 13 Distillation Crucible & UMA-bounded QLoRA geometric tuner"
```

---

## Self-Review Checklist (Completed)

- All three numbered sections of the user's Phase 13 directive are mapped to concrete tasks (E2E demo, QLoRA stub with strict constraints, evidence).
- Every new file will carry the required WORMHOLE-PATH1 manifest.
- The QLoRA stub is deliberately aggressive on memory constraints (4-bit base, r=8, targeted modules, 8-bit optimizer, gradient checkpointing, Δλ₁-weighted loss).
- The plan re-uses every previously delivered Phase 11/11.2 component instead of reinventing them.
- TDD + small commits + exact commands are specified throughout.
- No placeholders.

**Plan complete and saved to** `prime-crystal-grok/docs/superpowers/plans/2026-06-04-phase-13-distillation-crucible-qlora-synthesis.md`

**Execution options (as before):**

1. **Subagent-Driven (recommended)** – Fresh subagent per task with two-stage review.
2. **Inline Execution** – We run the TDD loops together here.

Which would you like? (Reply with "1" or "2".) 

The crucible is ready. The engine is about to learn how to eat its own intelligence at scale.