"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/tui-layer/integration/transducer_graft.py
Transducer Bridge — Safe Grafting Logic (Phase 4)

Zero-pollution reference implementation plan for lifting proven code from
manus-plugin-dev-session-current-4 into the clean seed.

This file contains:
- Interface contracts
- Safe lifting patterns (comment-only references to old logic)
- Adapter wiring points

Never copy-paste code from the old session. Re-implement with full AXiomZ traceability.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Dict

# Local clean imports
from ..adapter.rich_prime_event_builder import RichPrimeEventBuilder
from ..state.term_series import CurrentStalkBundle


class TransducerGraft:
    """
    The bridge that allows the clean seed to consume real stalk data
    while keeping all implementation inside the zero-pollution tree.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.builder = RichPrimeEventBuilder()

    def get_enriched_event(self, trigger: str) -> dict[str, Any]:
        """
        Primary entry point for the SurfaceEnclosure and future PrimeTopologicalSpace.

        This is where the old transducer's build_from_project logic will be grafted
        in subsequent slices (re-implemented, not imported).
        """
        event = self.builder.build_from_project(
            project_dir=self.project_root,
            trigger=trigger
        )
        # Future: here we will inject the old crystallize_to_prime, real L_F path,
        # and the three canonical intents (encode_system_state, compute_cryptologic_key, verify_coherence).
        return event

    # ------------------------------------------------------------------
    # Grafting Reference Notes (do not execute, for planning only)
    # ------------------------------------------------------------------
    #
    # From old session (read-only reference):
    # - prime_transducer.py:RichPrimeEventBuilder.build_from_project
    #   - Used 9D vectors + AST + lifecycle stage features
    #   - Produced restriction_map_sparse as csr_matrix
    #
    # Safe lift pattern:
    # 1. Re-implement the feature extraction logic here with full 9D definition.
    # 2. Add the _crystallize_to_prime method (prime-basis quantization).
    # 3. Wire the output directly into SurfaceEnclosure.enclose_and_execute
    #    as the build_stalks callable.
    #
    # MaxOp constraints to preserve:
    # - Keep restriction maps sparse (target < 5-10% density for NPU/ARM64)
    # - Prefer int8 / prime-weighted values where possible
    # - No dense numpy matrices on hot paths
    #
    # Next concrete step after this file:
    # - Implement a production-grade feature extractor that matches or exceeds
    #   the old smoke_test_rich_prime_builder_1.2.py results.
    # ------------------------------------------------------------------


def make_grafted_stalk_builder(graft: TransducerGraft) -> Callable[[str], CurrentStalkBundle]:
    """
    Factory that turns the graft into a drop-in build_stalks function
    for SurfaceEnclosure.enclose_and_execute.
    """
    def build_stalks(trigger: str) -> CurrentStalkBundle:
        event = graft.get_enriched_event(trigger)
        # Convert dict form to CurrentStalkBundle (light adapter)
        return CurrentStalkBundle(
            trigger=trigger,
            node_data=event["node_data"],
            edge_data=event["edge_data"],
            meta=event.get("meta", {})
        )
    return build_stalks
