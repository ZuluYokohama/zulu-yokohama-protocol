"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/tui-layer/persistence/persistent_fabric.py
Persistent Fabric — The TUI Overlay for Continuous Conscious Operation (Phase 5.1)

This module makes the Reality Bridge persistent across the entire developer session.

Key features:
- Loads/saves the current ActiveTermSeries + full K(S) history to disk.
- Every new "prompt" or tool call in the Grok TUI is treated as the next term in the *ongoing* diffusion.
- Δλ₁ is always computed against the previous manifold state (not reset baseline).
- Provides PersistentSurfaceEnclosure that carries state forward.

This is the "nervous system" binding. The engine no longer forgets between prompts.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime, timezone

from ..state.term_series import ActiveTermSeries, CryptologicKey, CurrentStalkBundle
from ..enforcement.surface_enclosure import SurfaceEnclosure
from ..integration.transducer_graft import TransducerGraft, make_grafted_stalk_builder


class PersistentFabric:
    """
    The persistent state manager for the Grok TUI under Prime Crystal protocol.

    Maintains one continuous ActiveTermSeries for the lifetime of the developer's session
    (or until explicit reset).
    """

    def __init__(self, seed_root: Path, session_id: Optional[str] = None):
        self.seed_root = Path(seed_root).resolve()
        self.persistence_dir = self.seed_root / "evidence" / "persistence"
        self.persistence_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or f"persistent-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self.state_file = self.persistence_dir / f"{self.session_id}.json"

        self.series: Optional[ActiveTermSeries] = None
        self.enclosure: Optional[SurfaceEnclosure] = None

        self._load_or_initialize()

    def _load_or_initialize(self):
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct minimal series (in real system this would be richer)
            baseline = CryptologicKey(**data["baseline_k"])
            self.series = ActiveTermSeries(
                session_id=data["session_id"],
                start_k=baseline,
                value_function=data.get("value_function", {})
            )

            # Replay history if present
            for k_dict in data.get("ks_history", []):
                k = CryptologicKey(**k_dict)
                self.series.ks_history.append(k, 0.0)  # deltas replayed separately in real impl

            print(f"[PersistentFabric] Loaded existing session: {self.session_id}")
        else:
            # Fresh session — bootstrap from current project state
            graft = TransducerGraft(self.seed_root)
            event = graft.get_enriched_event("persistent_session_start")

            from ..adapter.prime_topological_space import PrimeTopologicalSpace
            space = PrimeTopologicalSpace(event)
            space.compute_sheaf_laplacian()
            lambda_1, _ = space.compute_spectral_gap()
            dim_h0 = space.compute_homology_dimension()

            baseline = CryptologicKey(
                dim_h0=dim_h0,
                lambda_1=lambda_1,
                holonomy_signature=space.detect_holonomy()
            )

            self.series = ActiveTermSeries(
                session_id=self.session_id,
                start_k=baseline,
                value_function={"phase": "Phase 5.1 Persistent Fabric"}
            )

            print(f"[PersistentFabric] Initialized new persistent session: {self.session_id}")
            print(f"    Baseline λ₁: {lambda_1:.6f}   dim H⁰: {dim_h0}")

        # Always create a fresh enclosure wired to the current series
        self._rewire_enclosure()

    def _rewire_enclosure(self):
        graft = TransducerGraft(self.seed_root)
        build_stalks = make_grafted_stalk_builder(graft)
        self.enclosure = SurfaceEnclosure(self.series)

        # Monkey-patch the build_stalks inside the enclosure for persistence
        # (In a real TUI runtime this would be cleaner dependency injection)
        original_enclose = self.enclosure.enclose_and_execute

        def persistent_enclose(trigger: str, **kwargs):
            # Force the persistent builder
            if "build_stalks" not in kwargs or kwargs["build_stalks"] is None:
                kwargs["build_stalks"] = lambda t: build_stalks(trigger)
            return original_enclose(trigger, **kwargs)

        self.enclosure.enclose_and_execute = persistent_enclose

    def get_current_ks(self) -> Dict[str, Any]:
        """Return the live K(S) of the persistent manifold."""
        if self.series is None:
            return {}

        current = self.series.current_k()
        return current.to_dict() if hasattr(current, "to_dict") else {
            "lambda_1": getattr(current, "lambda_1", 0.0),
            "dim_h0": getattr(current, "dim_h0", 0),
            "holonomy": getattr(current, "holonomy_signature", "unknown")
        }

    def save(self):
        """Persist the current state to disk (called after every significant term)."""
        if self.series is None:
            return

        data = {
            "session_id": self.series.session_id,
            "baseline_k": self.series.start_k.to_dict() if hasattr(self.series.start_k, "to_dict") else {},
            "ks_history": [k.to_dict() if hasattr(k, "to_dict") else {} for k in self.series.ks_history.keys],
            "value_function": self.series.value_function,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"[PersistentFabric] State saved for session {self.session_id}")

    def evolve(self, trigger: str, proposed_action: Any) -> Dict[str, Any]:
        """
        The main entry point for the Grok TUI.

        Every user prompt or tool call in the TUI should eventually route here.
        It treats the call as the next term in the *continuous* series.
        """
        if self.enclosure is None:
            self._rewire_enclosure()

        result = self.enclosure.enclose_and_execute(
            trigger=trigger,
            apply_action=lambda stalks: proposed_action
        )

        # Persist after every evolution
        self.save()

        return {
            "allowed": result.allowed,
            "current_ks": self.get_current_ks(),
            "delta_from_previous": result.emitted_k.lambda_1 - self.series.current_k().lambda_1 if result.emitted_k else 0.0,
            "blocked_reason": result.blocked_reason
        }


# Convenience factory for the Grok TUI
def get_persistent_fabric_for_tui(seed_root: Path) -> PersistentFabric:
    """The function the real Grok TUI runtime would call at session start."""
    return PersistentFabric(seed_root)
