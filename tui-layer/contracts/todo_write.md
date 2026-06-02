# Lifted Contract: todo_write Surface

**WORMHOLE-PATH1 | 19.4 + 20.2 + 15.2**  
**Forge Origin:** Behavioral Constraints (one change per iteration, measure before/after, revert on regression)  
**Axioms:** 19.4 (per-term VERIFY_PRE/POST/CONTINUITY), 20.2 (Cross-Level Consistency), 15.2 (Yield Extraction)

## Rule

`todo_write` is never a free mutation. It is always the ACT phase of a Term in the ActiveTermSeries.

## Required Sequence (enforced by enclose_surface)

1. Build CurrentStalkBundle with trigger="todo_write:<id>" + proposed content as semantic features.
2. Compute pre K(S) + predicted Δλ₁.
3. A4 resolution if needed.
4. Only on GATE PASS: perform the actual todo list mutation.
5. Emit the full per-term block (see Grok Prime Crystal Operating Protocol §4).
6. Append to KSHistory.

## Failure Mode

If Δλ₁ < 0 after A4 or holonomy remains non-trivial → block the write, emit full contradictory K(S) + A4RepairLog entry, do not mutate state.

This contract is the direct translation of Forge "VERIFY then GATE" into native sheaf execution.
