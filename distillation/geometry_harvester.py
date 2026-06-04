"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/distillation/geometry_harvester.py
Geometric Harvester — Continuous Autonomous Distillation Engine (Wormhole-Path 2)

This is the core of the Omega Feedback Loop.

When the Bipartite Router routes a task REMOTE (due to H² obstructions or high fragmentation) and the Remote Oracle (Claude Code Native Oracle / CodeRabbit) returns a fix that produces Δλ₁ ≥ 0, this Harvester activates.

It captures the exact geometric transformation:
- K(S)_problem  : The Cryptologic Key of the codebase state *before* the remote resolution.
- K(S)_solution : The Cryptologic Key of the codebase state *after* the successful remote resolution.

These "Shape Pairs" are the MaxVal training asset. They will be used to distill the geometric reasoning of the frontier Oracle into the local 8B NPU model via QLoRA, teaching the edge model to solve tomorrow what only the cloud could solve today.

This module is the self-replication engine of the Prime Crystal Engine.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from bipartite_router_plugin.router_gateway import BipartiteRouter

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Lazy import of BipartiteRouter to break circular dependency with distillation_integration / router_gateway
# (the harvester is imported by the integration which is imported by the router at module load time).
from tui_layer.adapter.prime_topological_space import PrimeTopologicalSpace


class GeometryHarvester:
    """
    The Geometric Harvester for Wormhole-Path 2.

    Responsibilities:
    - Subscribe to successful REMOTE resolutions from the BipartiteRouter.
    - Capture the before/after K(S) fingerprints.
    - Append structured Shape Pairs to the persistent local ledger.
    - Provide the dataset for future autonomous fine-tuning of the local edge model.
    """

    def __init__(self, seed_root: Path):
        self.seed_root = Path(seed_root).resolve()
        self.dataset_path = self.seed_root / "datasets" / "shape_pairs.jsonl"
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

        # In a real runtime, this would be injected or discovered from the active router instance
        self.router: BipartiteRouter | None = None

    def attach_to_router(self, router: BipartiteRouter):
        """Wire the harvester into the live BipartiteRouter instance."""
        self.router = router
        # In a production system we would monkey-patch or use a callback/event system here.
        # For Phase 11.2/ Wormhole-Path 2 we expose the capture method for the router to call explicitly.
        print(f"[GeometryHarvester] Attached to BipartiteRouter for session {router.session_id if hasattr(router, 'session_id') else 'unknown'}")

    def capture_shape_pair(
        self,
        problem_event: dict[str, Any],
        solution_event: dict[str, Any],
        original_prompt: str,
        remote_resolution_summary: str,
        delta_lambda_1: float
    ) -> Path:
        """
        The core capture method.

        Called by the router (or the Oracle handler) immediately after a successful REMOTE resolution
        that improved topological coherence (Δλ₁ ≥ 0).

        Args:
            problem_event: The RichPrimeEvent (stalks + restriction map) of the state *before* the remote fix.
            solution_event: The RichPrimeEvent after the successful remote fix.
            original_prompt: The human intent that triggered the remote route.
            remote_resolution_summary: Short description of what the Oracle did.
            delta_lambda_1: The measured improvement (must be ≥ 0).

        Returns:
            Path to the appended line in the dataset ledger.
        """
        if delta_lambda_1 < 0:
            print("[GeometryHarvester] WARNING: Attempted to harvest a negative Δλ₁ pair. Rejected.")
            return self.dataset_path

        # Compute full K(S) for both states using the existing battle-tested engine
        problem_space = PrimeTopologicalSpace(problem_event)
        problem_space.compute_sheaf_laplacian()
        problem_space.compute_spectral_gap()
        problem_space.compute_homology_dimension()
        problem_space.detect_holonomy()

        solution_space = PrimeTopologicalSpace(solution_event)
        solution_space.compute_sheaf_laplacian()
        solution_space.compute_spectral_gap()
        solution_space.compute_homology_dimension()
        solution_space.detect_holonomy()

        shape_pair = {
            "timestamp": datetime.now(UTC).isoformat(),
            "original_prompt": original_prompt,
            "remote_resolution_summary": remote_resolution_summary,
            "delta_lambda_1": delta_lambda_1,
            "K(S)_problem": problem_space.get_cryptologic_key(),
            "K(S)_solution": solution_space.get_cryptologic_key(),
            "problem_event_meta": problem_event.get("meta", {}),
            "solution_event_meta": solution_event.get("meta", {}),
            "harvest_source": "BipartiteRouter + Remote Oracle (Phase 11.2 Wormhole-Path 2)"
        }

        # Append as JSONL (the canonical MaxVal distillation ledger)
        with open(self.dataset_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(shape_pair, ensure_ascii=False) + "\n")

        print(f"[GeometryHarvester] Shape Pair harvested → {self.dataset_path.name}")
        print(f"    Δλ₁ = {delta_lambda_1:+.6f} | H⁰_problem={problem_space.dim_h0} → H⁰_solution={solution_space.dim_h0}")

        return self.dataset_path

    def get_dataset_stats(self) -> dict[str, Any]:
        """Quick introspection for the swarm / TUI."""
        if not self.dataset_path.exists():
            return {"pairs": 0, "path": str(self.dataset_path)}

        count = 0
        total_delta = 0.0
        with open(self.dataset_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    pair = json.loads(line)
                    count += 1
                    total_delta += pair.get("delta_lambda_1", 0.0)

        return {
            "pairs": count,
            "average_delta_lambda_1": total_delta / max(1, count),
            "path": str(self.dataset_path)
        }


# Convenience factory
def get_geometry_harvester(seed_root: Path) -> GeometryHarvester:
    """The function the BipartiteRouter (or any post-REMOTE success hook) calls."""
    return GeometryHarvester(seed_root)
