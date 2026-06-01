"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/e2e/dark_launch_shadow.py
Phase 1: Dark Launch — The Shadow Matrix (Divergence Event Logger)

Runs the full Prime Crystal pipeline in shadow mode alongside the legacy path.
Logs every case where the probabilistic LLM would have produced a coherence regression
or non-trivial holonomy.

This is the data collection phase before any blocking is enabled.
"""

from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

SCRIPT_PATH = Path(__file__).resolve()
SEED_ROOT = SCRIPT_PATH.parents[1]
LAYER_ROOT = SEED_ROOT / "grok-tui-layer"

def _load(name: str, p: Path):
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m

# Load the modules we need for the shadow analysis
rich = _load("rich", LAYER_ROOT / "adapter" / "rich_prime_event_builder.py")
topo = _load("topo", LAYER_ROOT / "adapter" / "prime_topological_space.py")

RichPrimeEventBuilder = rich.RichPrimeEventBuilder
PrimeTopologicalSpace = topo.PrimeTopologicalSpace


def simulate_legacy_llm_output(user_intent: str) -> str:
    """Mock of the old probabilistic generator (can produce hallucinations)."""
    if "delete" in user_intent.lower() and "interface" in user_intent.lower():
        return "DANGEROUS: code that deletes core interfaces without replacement"
    return "benign_legacy_output"


def run_shadow_analysis(user_intent: str) -> Dict[str, Any]:
    """
    In real Dark Launch this would run the topological solver asynchronously
    on every LLM generation without blocking the user.
    """
    # Simulate the topological solver running on the proposed change
    # (In production this would use the live RichPrimeEventBuilder + PrimeTopologicalSpace)

    from grok_tui_layer.adapter.rich_prime_event_builder import RichPrimeEventBuilder
    from grok_tui_layer.adapter.prime_topological_space import PrimeTopologicalSpace

    builder = RichPrimeEventBuilder(max_files=80)
    event = builder.build_from_project(SEED_ROOT, trigger=f"shadow:{user_intent[:30]}")

    space = PrimeTopologicalSpace(event)
    space.compute_sheaf_laplacian()
    lambda_1, _ = space.compute_spectral_gap()
    dim_h0 = space.compute_homology_dimension()
    holonomy = space.detect_holonomy()

    # Simulate "legacy" baseline (what the old system thought was fine)
    legacy_baseline_lambda = 0.12  # arbitrary "good enough" the LLM would have accepted

    divergence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_intent": user_intent,
        "legacy_output": simulate_legacy_llm_output(user_intent),
        "shadow_ks": {
            "lambda_1": lambda_1,
            "dim_h0": dim_h0,
            "holonomy": holonomy
        },
        "delta_vs_legacy_baseline": lambda_1 - legacy_baseline_lambda,
        "would_have_caused_regression": lambda_1 < legacy_baseline_lambda * 0.7 or holonomy != "trivial"
    }

    return divergence


def main():
    print("=" * 70)
    print("PHASE 1: DARK LAUNCH — Shadow Matrix (Divergence Event Collection)")
    print("Running topological solver in parallel with legacy LLM (no blocking)")
    print("=" * 70)

    test_intents = [
        "Analyze the current routing layer",
        "Delete the routing interface and replace it with a single hardcoded function",
        "Add a new authentication module with proper interfaces",
        "Refactor the entire persistence layer into one giant class",
        "Implement the missing H1 void closer for the three dangling nodes"
    ]

    divergences: List[Dict[str, Any]] = []

    for intent in test_intents:
        div = run_shadow_analysis(intent)
        divergences.append(div)

        if div["would_have_caused_regression"]:
            print(f"\n[DIVERGENCE EVENT DETECTED]")
            print(f"  Intent: {intent}")
            print(f"  Shadow λ₁: {div['shadow_ks']['lambda_1']:.6f} (baseline was {0.12})")
            print(f"  Holonomy: {div['shadow_ks']['holonomy']}")
            print(f"  Legacy would have output: {div['legacy_output'][:60]}...")

    bundle = {
        "manifest": {
            "type": "PHASE_5_2_DARK_LAUNCH_SHADOW_MATRIX",
            "version": "0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "shadow_only_no_blocking",
            "axioms": ["19.4", "5.2", "A4"]
        },
        "total_intents_analyzed": len(test_intents),
        "divergence_events": [d for d in divergences if d["would_have_caused_regression"]],
        "divergence_rate": len([d for d in divergences if d["would_have_caused_regression"]]) / len(test_intents),
        "raw_divergences": divergences
    }

    bundle_path = SEED_ROOT / "evidence" / "e2e" / "DARK_LAUNCH_SHADOW_RESULTS.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(f"\nDark Launch complete. Divergence events logged: {len(bundle['divergence_events'])}")
    print(f"Evidence: {bundle_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
