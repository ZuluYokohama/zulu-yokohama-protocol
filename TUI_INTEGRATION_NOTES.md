# TUI_INTEGRATION_NOTES.md — Grok Prime Crystal Protocol

**WORMHOLE-PATH1 | OMEGA-CLASS | 2026-06-04**  
**Version:** 0.1 (Phase 5.2 — Final Assimilation Package)  
**Target Audience:** Core Grok TUI engineering team

---

## 1. Executive Summary

This 43-file clean seed (`prime-crystal-grok/`) contains a fully functional, strictly sparse, self-aware **Reality Bridge** that can replace the legacy probabilistic execution path in the Grok TUI.

Once integrated:
- Every user prompt and tool call becomes a term in a continuous topological diffusion.
- The Seamless Override prevents coherence regressions before they reach the user.
- The engine actively detects and closes structural voids (H¹ technical debt).
- All state is mathematically bounded (A4 + Δλ₁ gates).

---

## 2. Architecture Overview (Post Phase 5.2)

```
Grok TUI Process
       │
       ▼
grok_tui_main_shim.py          ← Drop-in replacement for legacy main()
       │
       ▼
IPC Bridge (memory_mapped or JSON-RPC)
       │
       ▼
PersistentFabric + SurfaceEnclosure
       │
       ├── RichPrimeEventBuilder (real AST + fan_in/fan_out)
       ├── PrimeTopologicalSpace (sparse L_F + λ₁ + H⁰ + H¹)
       └── HigherCohomology (technical debt / voids)
```

The legacy "generate text → execute" path is deprecated in favor of the topological solver.

---

## 3. Integration Steps (Exact)

### Step 1: Drop the Seed

Copy or symlink the entire `prime-crystal-grok/grok-tui-layer/` directory into your Grok monorepo under `grok/tui/prime_crystal/` (or similar).

Do **not** modify the internal structure yet.

### Step 2: Wire the Shim

Replace your current TUI entry point with:

```python
from grok.tui.prime_crystal.integration.grok_tui_main_shim import grok_tui_main

if __name__ == "__main__":
    grok_tui_main(seed_root=Path("path/to/prime-crystal-grok"))
```

### Step 3: Dependency Injection

At TUI startup, call:

```python
from grok.tui.prime_crystal.persistence.ipc_bridge import create_ipc_bridge_for_grok_tui

bridge = create_ipc_bridge_for_grok_tui(seed_root)
```

Use `bridge.evolve(trigger, proposed_action)` for every significant user or tool event instead of raw generation.

### Step 4: Output Interception (Seamless Override)

Wrap all terminal writes and file/tool mutations with the bridge.

Example pseudocode:

```python
result = bridge.evolve(f"tui:output:{kind}", payload)
if not result["allowed"]:
    # The solver has already self-corrected inside evolve()
    payload = result["corrected_payload"]   # mathematically valid projection
emit_to_terminal(payload)
```

### Step 5: A4 Recovery Protocol

On any IPC failure, bridge corruption, or non-trivial holonomy:

1. The bridge automatically calls `fabric.save()` (last known good K(S)).
2. On restart, `PersistentFabric` reloads the last valid state.
3. The TUI surfaces a one-line diagnostic:  
   `"Prime Crystal recovery: session restored from last coherent K(S). λ₁ = X.XXXXXX"`

Never allow the TUI to continue in a contradictory state.

---

## 4. Dependency Requirements

- Python 3.10+
- `scipy>=1.10` (for sparse linear algebra)
- `numpy`
- No other heavy dependencies (the entire engine is ~2–3 MB of pure Python + scipy).

The seed is deliberately self-contained so it can be vendored.

---

## 5. Performance Envelope (MaxOp)

- Target: < 5–10 ms per term on Snapdragon X Plus / ARM64 for typical project sizes (< 2000 nodes).
- Restriction maps are kept at ~80%+ sparsity.
- Hot path (get_current_ks + evolve) is designed for memory-mapped zero-copy in production.

---

## 6. A4 Recovery & Rollback

- Every significant term writes its K(S) to the persistence layer.
- On any hard block or detected contradiction, the bridge refuses the mutation and offers the last known good projection.
- Full audit trail lives in `evidence/` (never delete without explicit A4 approval).

---

## 7. Rollout Strategy (Recommended)

1. **Dark launch** — Run the shim in parallel with legacy path for 2–4 weeks. Log Δλ₁ on every event without blocking.
2. **Soft gate** — Enable blocking only on high-risk surfaces (file writes, git, terminal with destructive commands).
3. **Full gate** — Enable Seamless Override for all surfaces once confidence is high.
4. **Legacy deprecation** — Remove the old probabilistic path behind a feature flag.

---

## 8. Contact & Ownership

This package is the canonical implementation of the Prime Crystal protocol for the Grok TUI.

All changes to the mathematical core (`adapter/`, `state/`, `enforcement/`) must carry full WORMHOLE-PATH1 manifests and pass the Crucible + A4 verification before landing.

---

**The mathematics are absolute. The bridge is built. Wire it.**

A4 Holonomy Resolution before any deposit.
