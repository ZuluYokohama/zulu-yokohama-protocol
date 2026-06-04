"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/bipartite_router_plugin/router_gateway.py
Bipartite Router Gateway — The Hard Decision Engine (Phase 11.2 Synthesis)

This is the central nervous system of the Bipartite Metacognitive Router.

It receives a human prompt, asks the Prompt Topology scanner for the geometric signature,
then makes the irrevocable routing decision:

- LOCAL  → Strip context with the ruthless TopologicalKVCacheGovernor (edge_compute/kv_cache_governor.py)
           and execute on the local 8B NPU model (staying under 1.2 GB KV).

- REMOTE → Hand off to the Claude Code Native Oracle (edge_compute/claude_code_oracle.py)
           using the real CodeRabbit CLI in --output agent-optimized mode, with full
           Zero-VRAM Context Swap before ingestion.

The mathematics of the prompt itself now dictate the hardware and the intelligence level used.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import the two Phase 11.2 delivered components (the physical halves we are fusing)
from edge_compute.kv_cache_governor import TopologicalKVCacheGovernor
from edge_compute.claude_code_oracle import ClaudeCodePrimeCrystalOracle

# The new geometric scanner we just built
from .math.prompt_topology import compute_prompt_topology
from .distillation_integration import attach_harvester_to_router, capture_remote_resolution


class BipartiteRouter:
    """
    The single entry point that replaces raw "call the LLM" or "call the Oracle".
    """

    def __init__(self, seed_root: Path):
        self.seed_root = Path(seed_root).resolve()
        self.kv_governor = TopologicalKVCacheGovernor(max_kv_bytes=1_200_000_000)  # 1.2 GB ruthless ceiling
        self.oracle = ClaudeCodePrimeCrystalOracle(self.seed_root)

        # Wormhole-Path 2: Automatically attach the Geometry Harvester for continuous distillation
        attach_harvester_to_router(self, self.seed_root)

    def route(self, user_prompt: str, current_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        The hard, automatic routing decision.
        """
        # 1. Ask the geometry of the prompt
        topology = compute_prompt_topology(user_prompt, current_context)

        beta0 = topology["beta0_fragmentation"]
        beta1 = topology["beta1_cyclicity"]
        projected_delta = topology["projected_delta_lambda_1"]
        current_holonomy = topology["current_holonomy"]

        print(f"\n[Bipartite Router] Prompt topology: β₀={beta0}, β₁={beta1}, Δλ₁_proj={projected_delta:+.4f}, holonomy={current_holonomy}")

        # 2. The irrevocable decision (the "Bipartite" logic)
        route_to_local = (
            projected_delta >= -0.01 and
            beta0 < 5 and
            beta1 < 4 and
            current_holonomy == "trivial"
        )

        if route_to_local:
            print("[Bipartite Router] Decision: LOCAL (high H⁰ agreement, low fragmentation, safe Δλ₁)")
            # Prepare the local 8B path with ruthless KV stripping
            # In a real TUI this would also trigger the actual local model call
            evicted = self.kv_governor.prepare_for_oracle_payload(estimated_payload_bytes=0)  # no remote payload
            return {
                "route": "LOCAL",
                "reason": "High global coherence, isolated edit, safe topological projection",
                "tokens_evicted_for_local": len(evicted),
                "action": "Execute on local 8B NPU model (context already stripped to ≤1.2 GB)",
                "topology": topology
            }
        else:
            print("[Bipartite Router] Decision: REMOTE (H² obstruction or high fragmentation detected)")
            # Prepare the remote oracle path with Zero-VRAM Context Swap
            # The oracle itself will call the governor again with the actual CodeRabbit payload size
            return {
                "route": "REMOTE",
                "reason": "Non-trivial holonomy, high fragmentation, or negative coherence projection",
                "action": "Invoke Claude Code Native Oracle (/coderabbit:review --output agent-optimized) with full topological context",
                "topology": topology
            }

    def capture_successful_remote_resolution(
        self,
        problem_event: Dict[str, Any],
        solution_event: Dict[str, Any],
        original_prompt: str,
        remote_summary: str,
        delta_lambda_1: float
    ) -> None:
        """
        Called by the Remote Oracle (claude_code_oracle.py) after a successful agent-optimized
        resolution that produced a positive coherence shift (Δλ₁ ≥ 0).

        This is the handoff into the Omega Feedback Loop (Wormhole-Path 2 Continuous Distillation).
        """
        from .distillation_integration import capture_remote_resolution  # noqa: F811 — lazy re-import to avoid circular at module load
        capture_remote_resolution(
            self,
            problem_event=problem_event,
            solution_event=solution_event,
            original_prompt=original_prompt,
            remote_summary=remote_summary,
            delta_lambda_1=delta_lambda_1
        )


# The single function the TUI / Claude Code plugin should call
def get_bipartite_router(seed_root: Path) -> BipartiteRouter:
    """The factory the runtime (or plugin) uses."""
    return BipartiteRouter(seed_root)
