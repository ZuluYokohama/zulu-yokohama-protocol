"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/bipartite_router_plugin/distillation_integration.py
Distillation Integration Layer (Wormhole-Path 2)

This tiny module wires the GeometryHarvester into the BipartiteRouter's post-REMOTE success path.

In a real deployment, after the Remote Oracle (claude_code_oracle) returns a fix that improves coherence,
this integration captures the before/after geometric states and appends a Shape Pair to the ledger.

This is the self-replication / continuous distillation engine.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bipartite_router_plugin.router_gateway import BipartiteRouter

# NOTE: Router import is lazy to break circular dependency with router_gateway
# (router_gateway imports this module at top level for the capture handoff).
# Path bootstrap + absolute (consistent with other Phase 11.2 modules)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from distillation.geometry_harvester import get_geometry_harvester


def attach_harvester_to_router(router: BipartiteRouter, seed_root: Path) -> None:
    """
    One-time wiring call (called at router initialization or TUI boot).

    After this, every successful REMOTE resolution that improves Δλ₁ ≥ 0
    will automatically contribute to the autonomous distillation dataset.
    """
    harvester = get_geometry_harvester(seed_root)

    # Store reference on the router instance for later use by the oracle handler
    router._harvester = harvester  # type: ignore[attr-defined]

    # In a production system the router would have an event/callback system.
    # For this clean-seed implementation we expose a convenience method the oracle can call.
    print("[Distillation] GeometryHarvester attached to BipartiteRouter.")


def capture_remote_resolution(
    router: BipartiteRouter,
    problem_event: dict[str, Any],
    solution_event: dict[str, Any],
    original_prompt: str,
    remote_summary: str,
    delta_lambda_1: float
) -> None:
    """
    Called by the Remote Oracle handler (claude_code_oracle.py) immediately after
    a successful agent-optimized resolution that improved topological coherence.

    This is the actual handoff point that feeds the Omega Feedback Loop.
    """
    harvester = getattr(router, "_harvester", None)
    if harvester is None:
        print("[Distillation] WARNING: Harvester not attached to router. Shape pair not captured.")
        return

    harvester.capture_shape_pair(
        problem_event=problem_event,
        solution_event=solution_event,
        original_prompt=original_prompt,
        remote_resolution_summary=remote_summary,
        delta_lambda_1=delta_lambda_1
    )
