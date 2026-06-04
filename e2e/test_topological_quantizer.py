"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/e2e/test_topological_quantizer.py
TDD Test: TopologicalQuantizer GGUF/QNN Bridge (Phase 11 Task 2)

Validates that 4/5-bit mixed-precision quantization (with 8-bit salient weights)
preserves the core topological invariants (λ₁ spectral gap, dim H⁰, holonomy)
computed by PrimeTopologicalSpace.

This is the failing test that drives the minimal implementation of
edge_compute/topological_quantizer.py per the TDD mandate.

Axiomatic Dependencies:
- MaxOp Hardware Axioms + ARM64 UMA Optimization Doctrine (6GB envelope, zero-copy csr_matrix routing to NPU/QNN, asymmetric precision, FRSQRTE for normalizations)
- Phase 3/4/8/9 sparse L_F + H^k preservation
- Evidence bundles as source of truth for calibration events

The test uses a hermetic synthetic calibration event (small, reproducible, known-good λ₁/H⁰)
to avoid external deps or variable project scans during the unit TDD loop.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Dict

# SEED_ROOT for bootstrap (required to make literal plan imports work on hyphenated dir + new edge_compute/)
SCRIPT_PATH = Path(__file__).resolve()
SEED_ROOT = SCRIPT_PATH.parents[1]


def load_calibration_event() -> dict[str, Any]:
    """
    Phase 11 TDD helper: Return a small, deterministic 'known-good' event.
    When fed to PrimeTopologicalSpace + compute_* it yields stable positive λ₁ and dim H⁰ >= 1.
    Synthetic (not full project scan) for speed, reproducibility, and MaxOp compliance in CI.
    """
    from scipy.sparse import csr_matrix

    n = 25
    row: list[int] = []
    col: list[int] = []
    data: list[float] = []

    # Identity (self-loops) + light containment edges (mimics builder output)
    for i in range(n):
        row.append(i)
        col.append(i)
        data.append(1.0)

    for i in range(0, n - 1, 3):
        if i + 1 < n:
            row.extend([i, i + 1])
            col.extend([i + 1, i])
            data.extend([0.75, 0.75])

    rmap = csr_matrix((data, (row, col)), shape=(n, n))

    node_data = [
        {
            "id": f"n{i}",
            "kind": "FunctionDef",
            "file": "calibration.py",
            "feature": [2.0, float(i % 5), 1.0, 2.0, 1.0, 3.0, 1.0, 0.0, 10.0],
            "lineno": 10 + i,
        }
        for i in range(n)
    ]

    return {
        "trigger": "calibration:synthetic:phase11-quant-tdd",
        "node_data": node_data,
        "edge_data": [],
        "restriction_map_sparse": rmap,
        "meta": {
            "builder_version": "phase11-tdd-synthetic",
            "nodes_extracted": n,
            "source": "e2e/test_topological_quantizer.py:load_calibration_event",
        },
    }


def test_4bit_quantization_preserves_lambda_1():
    """
    Exact test body from Phase 11 plan (with load_calibration_event resolved + bootstrap
    to support the literal 'from tui_layer...' and 'from edge_compute...' imports).
    """
    # === Bootstrap for import compatibility (hyphen dir + root packages) ===
    # Matches patterns used in dark_launch_shadow.py and internal adapter path hacks.
    # Allows the test source to contain the *exact* import lines specified in the plan.
    if str(SEED_ROOT) not in sys.path:
        sys.path.insert(0, str(SEED_ROOT))

    LAYER_ROOT = SEED_ROOT / "tui_layer"

    # Create namespace package entries so "from tui_layer.adapter.xxx" resolves
    # using the on-disk hyphen dir (without renaming files or requiring editable install).
    if "tui_layer" not in sys.modules:
        grok_pkg = types.ModuleType("tui_layer")
        grok_pkg.__path__ = [str(LAYER_ROOT)]
        sys.modules["tui_layer"] = grok_pkg

    if "tui_layer.adapter" not in sys.modules:
        adapter_pkg = types.ModuleType("tui_layer.adapter")
        adapter_pkg.__path__ = [str(LAYER_ROOT / "adapter")]
        sys.modules["tui_layer.adapter"] = adapter_pkg

    if "tui_layer.higher_cohomology" not in sys.modules:
        hc_pkg = types.ModuleType("tui_layer.higher_cohomology")
        hc_pkg.__path__ = [str(LAYER_ROOT / "higher_cohomology")]
        sys.modules["tui_layer.higher_cohomology"] = hc_pkg

    if "tui_layer.persistence" not in sys.modules:
        pers_pkg = types.ModuleType("tui_layer.persistence")
        pers_pkg.__path__ = [str(LAYER_ROOT / "persistence")]
        sys.modules["tui_layer.persistence"] = pers_pkg

    if "tui_layer.integration" not in sys.modules:
        int_pkg = types.ModuleType("tui_layer.integration")
        int_pkg.__path__ = [str(LAYER_ROOT / "integration")]
        sys.modules["tui_layer.integration"] = int_pkg

    if "tui_layer.state" not in sys.modules:
        state_pkg = types.ModuleType("tui_layer.state")
        state_pkg.__path__ = [str(LAYER_ROOT / "state")]
        sys.modules["tui_layer.state"] = state_pkg

    if "tui_layer.enforcement" not in sys.modules:
        enf_pkg = types.ModuleType("tui_layer.enforcement")
        enf_pkg.__path__ = [str(LAYER_ROOT / "enforcement")]
        sys.modules["tui_layer.enforcement"] = enf_pkg

    # The adapter .py files themselves insert their local dirs into sys.path for sibling imports
    # (e.g. prime_topological_space imports rich_prime_event_builder via its hack).
    # Our namespace setup + root in path makes the top-level "from tui_layer..." succeed.

    # Now the literal imports from the plan:
    from edge_compute.topological_quantizer import TopologicalQuantizer
    from tui_layer.adapter.prime_topological_space import PrimeTopologicalSpace

    # === Test body (per plan) ===
    # Use a small known-good event from previous evidence (synthetic calibration here)
    event = load_calibration_event()
    space = PrimeTopologicalSpace(event)
    space.compute_sheaf_laplacian()
    baseline_lambda, _ = space.compute_spectral_gap()
    _ = space.compute_homology_dimension()

    quantizer = TopologicalQuantizer(precision="Q4_K_M", calibration_space=space)
    quantized_ref = quantizer.quantize_model("path/to/base-8b.gguf")

    scores = space.verify_topological_invariants(quantized_ref)
    assert scores["lambda_1_preservation"] >= 0.95, (
        f"lambda_1_preservation {scores['lambda_1_preservation']} < 0.95 threshold"
    )

    # Exercise the companion method added in Step 2.1
    overall_score = space.compute_invariant_preservation_score(scores)
    assert 0.90 <= overall_score <= 1.0, f"overall preservation score out of range: {overall_score}"

    print(f"[TDD-PASS] test_4bit_quantization_preserves_lambda_1 | "
          f"baseline_λ1={baseline_lambda:.6f} scores={scores} overall={overall_score:.3f}")


if __name__ == "__main__":
    # Allow direct execution for manual verification (python e2e/test_topological_quantizer.py)
    test_4bit_quantization_preserves_lambda_1()
