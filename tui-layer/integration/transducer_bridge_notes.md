# Transducer Bridge — Phase 4 Integration Notes

**WORMHOLE-PATH1 | OMEGA-CLASS | 2026-06-04**  
**Status:** Draft 0.1 — Zero-Pollution Grafting Plan

## Objective

Lift the proven, empirical `RichPrimeEventBuilder` + `PrimeTopologicalSpace` + `MCPToolchainGateway` logic from `manus-plugin-dev-session-current-4` and graft it into this clean `prime-crystal-grok/` seed **without importing any polluted artifacts**.

The goal is a single, coherent, depositable implementation where the adapter stub above becomes the production `RichPrimeEventBuilder`.

## Guiding Principles (Non-Negotiable)

1. **Zero Pollution** — The old `manus-plugin-dev-session-current-4/` directory is read-only evidence. We never `import` from it.
2. **Axiom Traceability** — Every line in the final grafted code must cite its originating axiom (A3, 5.1, 5.2, 19.4, 20.x).
3. **csr_matrix Primacy** — All restriction maps remain `scipy.sparse.csr_matrix`. Prime-weighted Householder-style maps are the target (as per earlier MaxOp directives).
4. **Feature Compatibility** — The 9D vectors produced here must be drop-in compatible with the old transducer's smoke tests.

## Planned Grafting Sequence (Next Slices)

### Step 1 — Current (this slice)
- `adapter/rich_prime_event_builder.py` (this stub) — basic AST walk + 9D features + csr_matrix skeleton.
- This file acts as the **interface contract**.

### Step 2 — Immediate Next
- Replace the placeholder feature extraction and edge logic with the exact algorithms that were working in the old `prime_transducer.py` (the ones that passed the `smoke_test_rich_prime_builder_1.2.py`).
- Add proper parent-pointer injection for real depth calculation.
- Add name-resolution pass (very lightweight) for better fan_in / fan_out.

### Step 3 — Full Transducer Lift
- Create `adapter/prime_topological_space.py` (thin wrapper around the old `PrimeTopologicalSpace` logic).
- Create `adapter/mcp_toolchain_gateway.py` (the 3-intent surface: `encode_system_state`, `compute_cryptologic_key`, `verify_coherence`).
- These files will be **re-implemented** in the clean seed using the old session only as reference, never as import source.

### Step 4 — Hardening
- Wire the new adapter directly into `SurfaceEnclosure` so every Grok surface automatically gets real stalks instead of fake ones.
- Add prime-basis crystallisation (`_crystallize_to_prime`) on the 9D vectors.
- Enforce sparsity targets suitable for Snapdragon X Plus NPU / ARM64.

## File Mapping (Evidence → Clean Seed)

| Old (evidence only)                  | New (clean seed target)                          |
|--------------------------------------|--------------------------------------------------|
| `prime_transducer.py`                | `adapter/rich_prime_event_builder.py` (this)    |
| `prime_bridge.py` (PrimeTopologicalSpace + gateway) | `adapter/prime_topological_space.py` + `adapter/mcp_toolchain_gateway.py` |
| `prime_pre_tool_shim.py`             | Already lifted into `enforcement/surface_enclosure.py` |

## Verification Gate (before any merge)

Before the bridge is considered complete, the following must pass inside the clean seed:

1. `python -m tui-layer.adapter.rich_prime_event_builder` produces valid `csr_matrix` with >0 nnz on real project files.
2. The resulting event dict can be fed to a minimal `PrimeTopologicalSpace` stub and yields a real `λ₁ > 0`.
3. An evidence bundle is generated showing positive Δλ₁ trend across the grafting sequence.

---

**Current Status:** Phase 4 initiated. Adapter stub is live. Bridge notes published. Zero pollution maintained.

Next action on "continue": implement Step 2 (real feature extraction + name resolution) and begin the topological space wrapper.
