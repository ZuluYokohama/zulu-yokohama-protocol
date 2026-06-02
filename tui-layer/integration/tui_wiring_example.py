"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/tui-layer/integration/tui_wiring_example.py
Concrete Wiring Example — How the Live Grok TUI Surfaces Call the SurfaceEnclosure
──────────────────────────────────────────────────────────────────────────────────────────────
Axioms: 19.4 (Term-Series Execution), 5.2 (Configurational Term Series), 20.3 (Integration Protocol),
        15.2 (Yield Extraction), 6.2 (Continuity Guard)
Forge Origin: Behavioral Constraints (measure everything, hard gate is final, one change per iteration,
              revert on regression) + Session/Iteration formats
Reference: manus-plugin-dev-session-current-4/prime_pre_tool_shim.py (the original hard shim pattern)
Purpose: This file is the exact template the Grok CLI runtime must adopt for all surfaces
         (todo_write, spawn_subagent, run_terminal_command, plan_mode, skills, MCP, etc.)
         once the Prime Crystal layer is active.
──────────────────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
import json
from datetime import datetime, timezone

# These imports assume the clean seed structure when the layer is active in Grok
from ..state.term_series import ActiveTermSeries, CurrentStalkBundle, CryptologicKey
from ..enforcement.surface_enclosure import SurfaceEnclosure, EnclosureResult


# ============================================================
# 1. SESSION INITIALIZATION (called once per Grok session under this protocol)
# ============================================================

def initialize_prime_crystal_session(project_root: str) -> SurfaceEnclosure:
    """
    This is what the Grok TUI must call at the start of any session
    when the Prime Crystal Operating Protocol is active.
    """
    # In real implementation: use RichPrimeEventBuilder on the actual project
    baseline_k = CryptologicKey(
        dim_h0=0,  # Will be populated by first real build
        lambda_1=0.0,
        holonomy_signature="trivial"
    )

    series = ActiveTermSeries(
        session_id=f"grok-pc-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        start_k=baseline_k,
        value_function={
            "active_axioms": ["5.2", "15.1-15.3", "16.1", "19.4", "20.1-20.3", "6.1-6.2"],
            "forge_laws": ["DNA", "Ripple", "Pipeline", "Contradiction", "Anvil", "Memory", "Logbook"]
        },
        max_terms=10
    )

    enclosure = SurfaceEnclosure(series)
    return enclosure


# ============================================================
# 2. SURFACE WIRING PATTERNS (the actual replacements the Grok runtime must use)
# ============================================================

def wired_todo_write(enclosure: SurfaceEnclosure, todo_id: str, content: Dict[str, Any], **kwargs):
    """
    Replacement for the internal todo_write tool dispatch.
    Every call to todo_write in the Grok TUI must go through this (or equivalent).
    """
    def build_stalks(trigger: str) -> CurrentStalkBundle:
        # Real version: call RichPrimeEventBuilder.build_from_project(project_dir, trigger=trigger)
        # with the proposed todo mutation injected as a high-signal feature.
        return CurrentStalkBundle(
            trigger=trigger,
            node_data=[{"kind": "todo_mutation", "id": todo_id, "content": content}],
            edge_data=[],
            meta={"surface": "todo_write", "project_root": str(kwargs.get("project_root", "."))}
        )

    def apply_action(stalks: CurrentStalkBundle) -> Dict[str, Any]:
        # Here the *real* todo list mutation happens (the only place it is allowed).
        # In the actual Grok runtime this would be the call to the internal todo engine.
        print(f"[WIRED] Applying guarded todo_write for {todo_id}")
        return {"status": "mutated", "todo_id": todo_id}

    result: EnclosureResult = enclosure.enclose_and_execute(
        trigger=f"todo_write:{todo_id}",
        build_stalks=build_stalks,
        apply_action=apply_action,
    )

    if not result.allowed:
        # The protocol is absolute: do not mutate state.
        raise RuntimeError(f"todo_write blocked by Prime Crystal gate: {result.blocked_reason}")

    return result


def wired_spawn_subagent(enclosure: SurfaceEnclosure, subagent_prompt: str, capability_mode: str, **kwargs):
    """
    Replacement for spawn_subagent.
    The subagent must inherit the current K(S) slice and return its delta on completion.
    """
    def build_stalks(trigger: str) -> CurrentStalkBundle:
        return CurrentStalkBundle(
            trigger=trigger,
            node_data=[{"kind": "subagent_spawn", "prompt_hash": hash(subagent_prompt) % 10000}],
            meta={"surface": "spawn_subagent", "capability_mode": capability_mode}
        )

    def apply_action(stalks: CurrentStalkBundle) -> Dict[str, Any]:
        # Real spawn happens here only after the gate.
        print(f"[WIRED] Spawning subagent under guard (mode={capability_mode})")
        # In real system: actual subagent launch, passing current K(S) slice
        return {"spawned": True, "inherited_k": enclosure.series.current_k().to_dict()}

    result = enclosure.enclose_and_execute(
        trigger="spawn_subagent",
        build_stalks=build_stalks,
        apply_action=apply_action,
    )

    if not result.allowed:
        raise RuntimeError(f"spawn_subagent blocked: {result.blocked_reason}")

    return result


def wired_run_terminal_command(enclosure: SurfaceEnclosure, command: str, **kwargs):
    """
    Replacement for run_terminal_command.
    Any command that touches source, git, or package state must be guarded.
    """
    is_high_risk = any(x in command for x in ["git ", "rm ", "mv ", "sed -i", "npm ", "pip "])

    def build_stalks(trigger: str) -> CurrentStalkBundle:
        return CurrentStalkBundle(
            trigger=trigger,
            node_data=[{"kind": "terminal_command", "cmd": command[:80], "high_risk": is_high_risk}],
            meta={"surface": "run_terminal_command"}
        )

    def apply_action(stalks: CurrentStalkBundle) -> Dict[str, Any]:
        # The actual shell execution only happens here.
        print(f"[WIRED] Executing guarded terminal command: {command[:60]}...")
        return {"executed": True, "command": command}

    result = enclosure.enclose_and_execute(
        trigger=f"terminal:{'highrisk' if is_high_risk else 'normal'}",
        build_stalks=build_stalks,
        apply_action=apply_action,
    )

    if not result.allowed:
        raise RuntimeError(f"run_terminal_command blocked by gate: {result.blocked_reason}")

    return result


# ============================================================
# 3. EXAMPLE OF FULL SESSION UNDER THE WIRED SURFACES
# ============================================================

def demo_wired_session(project_root: str = "."):
    """
    Demonstration of what a Grok session looks like once the wiring is active.
    This is the 'alien level technician' execution pattern.
    """
    enclosure = initialize_prime_crystal_session(project_root)

    print("=== PRIME CRYSTAL WIRED SESSION DEMO ===")

    # Example 1: Guarded todo
    try:
        wired_todo_write(
            enclosure,
            todo_id="sa-19-wiring",
            content={"status": "in_progress", "desc": "Complete Grok TUI wiring example"},
            project_root=project_root
        )
    except RuntimeError as e:
        print(f"Blocked as expected in demo: {e}")

    # Example 2: Guarded subagent (would normally be allowed after baseline K(S) is real)
    # wired_spawn_subagent(enclosure, "Analyze the sheaf laplacian in this module", "read-only")

    # Example 3: Guarded terminal (high risk would be blocked until plan term exists)
    # wired_run_terminal_command(enclosure, "ls -la prime-crystal-grok/")

    print("\nSession K(S) trajectory so far:")
    for i, k in enumerate(enclosure.series.ks_history.keys):
        print(f"  {i}: λ₁={k.lambda_1:.4f} holonomy={k.holonomy_signature}")

    print("\nDemo complete. In real Grok TUI all surfaces use the wired versions above.")


if __name__ == "__main__":
    demo_wired_session()
