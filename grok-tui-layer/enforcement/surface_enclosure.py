"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/grok-tui-layer/enforcement/surface_enclosure.py
Universal Enclose Surface Choke Point — Zero-Bypass Term Execution Guard
──────────────────────────────────────────────────────────────────────────────────────────────
Axiomatic Dependencies: 19.4 (Term-Series Execution with mandatory guards),
                        6.2 (Continuity Guard), 4 / Law 4 (Contradiction → A4),
                        20.2 (Cross-Level Consistency), 15.2 (Yield Extraction)
Reference Implementation: manus-plugin-dev-session-current-4/prime_pre_tool_shim.py
                          (hard A4 block + sys.exit(1) pattern on Δλ₁ regression or non-trivial holonomy)
Prime Crystal: RichPrimeEventBuilder + real L_F + K(S) + Δλ₁ gate as the only execution path.
──────────────────────────────────────────────────────────────────────────────────────────────
This module is the single point through which EVERY Grok surface (tool call, todo mutation,
subagent spawn, terminal command, skill invocation, plan_mode, MCP, etc.) MUST pass.

It turns the abstract Grok Prime Crystal Operating Protocol into enforceable runtime logic.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
import sys
import traceback

# Import the core structures from the sibling state module
# In a real integrated Grok this would be absolute or properly packaged.
from ..state.term_series import (
    ActiveTermSeries,
    CurrentStalkBundle,
    TermSeriesExecutor,
    CryptologicKey,
    HolonomyEvent,
    Term
)


@dataclass
class EnclosureResult:
    """Result of attempting to execute a surface through the guard."""
    allowed: bool
    term: Optional[Term] = None
    error: Optional[str] = None
    blocked_reason: Optional[str] = None
    emitted_k: Optional[CryptologicKey] = None


class SurfaceEnclosure:
    """
    The universal zero-bypass guard for the Grok TUI / agent framework.

    Every major action the agent takes (the surfaces listed in the Protocol §3)
    must be wrapped by calling `enclose_and_execute(...)`.

    This is the direct realization of "hard A4 gate on all surfaces" and
    "the math itself is the runtime".
    """

    def __init__(self, series: ActiveTermSeries):
        self.series = series
        self.executor = TermSeriesExecutor(series)

    def enclose_and_execute(
        self,
        trigger: str,
        *,
        build_stalks: Callable[[str], CurrentStalkBundle],
        apply_action: Callable[[CurrentStalkBundle], Any],
        verify_pre: Optional[Callable[[CurrentStalkBundle], bool]] = None,
        verify_post: Optional[Callable[[CurrentStalkBundle, Any], bool]] = None,
        continuity_guard: Optional[Callable[[CryptologicKey, CryptologicKey], bool]] = None,
        on_block: Optional[Callable[[EnclosureResult], None]] = None,
    ) -> EnclosureResult:
        """
        The single choke point.

        This implements the full 19.4 term lifecycle with A4 holonomy resolution
        and hard Δλ₁ gate, exactly as required by the lifted Forge + AXiomZ protocol.
        """
        pre_k = self.series.current_k()

        try:
            # 1. Build the stalk bundle for this surface event (the "X" in 5.2)
            stalks = build_stalks(trigger)

            # 2. Execute the full guarded term (core of 19.4)
            term = self.executor.execute_term(
                trigger=trigger,
                build_stalks_fn=lambda t: stalks,
                apply_fn=apply_action,
                verify_pre_fn=verify_pre or (lambda s: True),
                verify_post_fn=verify_post or (lambda s, a: True),
                continuity_guard_fn=continuity_guard or (lambda before, after: after.is_trivial_holonomy()),
            )

            # 3. Hard gate logic (the "GATE" in Forge + A4 resolution)
            if not term.gate_passed:
                blocked_reason = self._diagnose_block(term, pre_k)
                result = EnclosureResult(
                    allowed=False,
                    term=term,
                    blocked_reason=blocked_reason,
                    emitted_k=term.post_k or pre_k
                )

                # Emit full contradictory K(S) + A4 trace (exactly as in prime_pre_tool_shim)
                self._emit_hard_block(result, term)

                if on_block:
                    on_block(result)
                return result

            # 4. Success path — action was applied under full topological guard
            result = EnclosureResult(
                allowed=True,
                term=term,
                emitted_k=term.post_k
            )
            return result

        except Exception as e:
            # Any uncaught exception during a term is treated as continuity violation
            error_k = CryptologicKey(
                dim_h0=pre_k.dim_h0,
                lambda_1=pre_k.lambda_1 - 0.5,  # punitive delta for failure to measure
                holonomy_signature="non-trivial:exception-during-term"
            )
            self.series.ks_history.append(error_k, -0.5)
            self.series.a4_log.record(HolonomyEvent(
                term_index=len(self.series.terms),
                before=pre_k,
                after=error_k,
                repair_actions=[f"Exception during enclose: {str(e)}"],
                success=False
            ))

            result = EnclosureResult(
                allowed=False,
                blocked_reason=f"Exception during guarded term: {str(e)}",
                emitted_k=error_k
            )
            self._emit_hard_block(result, None)
            if on_block:
                on_block(result)
            return result

    def _diagnose_block(self, term: Term, pre_k: CryptologicKey) -> str:
        if term.post_k and not term.post_k.is_trivial_holonomy():
            return f"Non-trivial holonomy after action: {term.post_k.holonomy_signature}"
        if term.delta_lambda_1 is not None and term.delta_lambda_1 < 0:
            return f"Coherence regression: Δλ₁ = {term.delta_lambda_1:.4f} (A4 repair insufficient)"
        return "One or more 19.4 guards failed (pre/post/continuity)"

    def _emit_hard_block(self, result: EnclosureResult, term: Optional[Term]) -> None:
        """
        The 'Drop the hammer' behavior — full transparent contradictory K(S) to stderr.
        This is the alien-level technician's immune response.
        Matches the spirit (and improves upon) the original prime_pre_tool_shim hard block.
        """
        print("\n" + "=" * 70, file=sys.stderr)
        print("HARD BLOCK — PRIME CRYSTAL ENFORCEMENT (19.4 + A4)", file=sys.stderr)
        print(f"Trigger: {term.trigger if term else 'unknown'}", file=sys.stderr)
        print(f"Reason: {result.blocked_reason}", file=sys.stderr)
        print(f"Pre K(S):  {result.emitted_k.to_dict() if result.emitted_k else 'N/A'}", file=sys.stderr)

        if term and term.post_k:
            print(f"Post K(S): {term.post_k.to_dict()}", file=sys.stderr)
            print(f"Δλ₁:       {term.delta_lambda_1}", file=sys.stderr)

        print("\nA4 Repair Log (current session):", file=sys.stderr)
        for event in self.series.a4_log.attempts[-3:]:  # last 3 for brevity
            print(f"  Term {event.term_index}: {'SUCCESS' if event.success else 'FAILED'} — {event.holonomy_signature if hasattr(event, 'holonomy_signature') else ''}", file=sys.stderr)

        print("\nFull contradictory K(S) emitted. Action REFUSED.", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)


# ============================================================
# Convenience wrapper for common Grok surfaces (the "linguistic layer")
# ============================================================

def make_todo_write_guard(enclosure: SurfaceEnclosure):
    """Returns a guarded version of todo_write that the Grok TUI can use."""
    def guarded_todo_write(todo_id: str, content: str, **kwargs):
        def build(trigger):
            # In real system: call RichPrimeEventBuilder with current project + this todo change
            return CurrentStalkBundle(
                trigger=trigger,
                node_data=[{"kind": "todo", "id": todo_id, "content": content}],
                meta={"surface": "todo_write"}
            )

        def apply(stalks):
            # Here the real todo list mutation would happen
            print(f"[GUARDED] todo_write applied for {todo_id}")
            return {"mutated": todo_id}

        result = enclosure.enclose_and_execute(
            trigger=f"todo_write:{todo_id}",
            build_stalks=build,
            apply_action=apply,
        )

        if not result.allowed:
            # The protocol says: do not perform the mutation
            raise RuntimeError(f"todo_write blocked by Prime Crystal gate: {result.blocked_reason}")

        return result

    return guarded_todo_write


# Example of how the live Grok would wire this (for future integration)
def example_wiring_for_grok_tui():
    """
    This shows the exact pattern the Grok CLI must adopt.
    In the final integrated system, the core agent loop calls these guarded versions
    instead of the raw todo_write / run_terminal_command / spawn_subagent etc.
    """
    # Assume we have an ActiveTermSeries already initialized for the session
    # series = ActiveTermSeries(...)
    # enclosure = SurfaceEnclosure(series)

    # todo_write = make_todo_write_guard(enclosure)
    # Then replace all internal calls to todo_write with the guarded version.

    print("Example wiring pattern defined. Ready for integration into Grok runtime.")
