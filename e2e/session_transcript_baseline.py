"""
ZULUYOKAHAMA PROTOCOL - e2e/session_transcript_baseline.py
Baseline Session K(S) from 37-Chapter Transcript Sequence (Phase 1 of meta-synthesis).

Minimal one-focused extractor using the local crystal engine on simple features
from sampled chapters + manifest.

Treats the sequence as development manifold. Computes real L_F + eigsh lambda1 + K(S)
as baseline for the transcript data. Quantity + qualia dimensioned starting point
for max-effect abstraction.

Per ZuluYokohama Protocol: manifests, clean, one-focused, evidence-oriented,
no agent/human names.

Run:
  cd C:/Users/Deving-1/Documents/dev/prime-crystal-grok
  $env:PYTHONPATH = "."
  python -Xutf8 e2e/session_transcript_baseline.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure we can import the sanitized engine (tui-layer dir + updated refs)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.sparse import csr_matrix

from tui_layer.adapter.prime_topological_space import PrimeTopologicalSpace


def build_minimal_session_event_from_chapters() -> dict[str, Any]:
    """
    Build a minimal RichPrimeEvent-like dict for the *entire 37-chapter sequence*
    as one "state" for baseline K(S).

    In full Phase 2/3 this will be per-chapter or sliding-window events with richer
    stalks from actual transcript text (system mentions, qualia tags, position).

    Here (Phase 1 baseline):
    - node_data: the "all systems" + qualia motifs distilled from sampling the 37
      (early design docs, mid A4/Δλ1 hard blocks with numbers, late pushes + protocol
      naming + "full structure" + "max effect" directive).
    - restriction_map_sparse: simple sequence path (adjacent chapters "connected")
      + some co-occurrence hyperedges for recurring systems (e.g. A4 appears in
      mid + echoed in late/37). Sparse for NPU/ARM affinity.
    - meta: sequence length, qualia summary, source note.

    This "dimensions" the sequence data properly for the engine's interp.
    """
    # The 37 "saves" as nodes in a path (sequence dimension)
    # (abbreviated labels for baseline; full Phase 2 will have rich per-chapter)
    nodes: list[dict[str, Any]] = [
        {"id": i, "label": f"chapter-{i:02d}"} for i in range(37)
    ]

    n = len(nodes)

    # Restriction map: sequence path (i -> i+1) + a few "system recurrence" hyperedges
    # (A4/holonomy/DeltaLambda1 appears mid and echoed in 37 "max effect")
    # + "clean seed / protocol naming" recurrence late.
    # Sparse csr for the engine.
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    # Path edges (sequence "time" dimension)
    for i in range(n - 1):
        rows += [i, i + 1]
        cols += [i + 1, i]
        data += [1.0, 1.0]

    # Co-occurrence / recurrence "hyperedges" (qualia/system motifs across "distance")
    # A4 / Delta / holonomy motif (mid 18 ↔ 37)
    rows += [17, 36, 36, 17]
    cols += [36, 17, 17, 36]
    data += [0.8, 0.8, 0.8, 0.8]

    # Clean seed / ZuluYokohama naming / full structure (late 36 ↔ 37)
    rows += [35, 36, 36, 35]
    cols += [36, 35, 35, 36]
    data += [0.9, 0.9, 0.9, 0.9]

    # Early design (01-02) ↔ late synthesis (37) — abstraction continuity
    rows += [0, 1, 36, 36]
    cols += [36, 36, 0, 1]
    data += [0.6, 0.6, 0.6, 0.6]

    restriction = csr_matrix((data, (rows, cols)), shape=(n, n))

    event: dict[str, Any] = {
        "node_data": nodes,
        "restriction_map_sparse": restriction,
        "meta": {
            "source": "io 37 chapter session transcripts sequence oriented saves",
            "phase": "ZuluYokohama Protocol meta-synthesis Phase 1 baseline",
            "sequence_length": 37,
            "qualia_summary": "mathematics as runtime, zero bypass, A4 on negative delta lambda1, one focused plus evidence with exact numbers, clean seed, sequence saves, protocol naming purity, max effect from proper dimensioning",
            "sampled_chapters": ["START 01", "02", "18", "36", "37 current directive"],
            "note": "Minimal synthetic event for baseline K(S). Full Phase 2 will use richer per-chapter stalks from actual transcript text via engine semantic tools."
        }
    }
    return event


def main() -> None:
    print("=" * 72)
    print("ZULUYOKAHAMA PROTOCOL — SESSION TRANSCRIPT BASELINE K(S) (Phase 1)")
    print("Source: io/ 37 chapters (sequence-oriented saves of the full work)")
    print("Engine: local tui-layer/adapter/prime_topological_space (sanitized)")
    print("=" * 72)

    event = build_minimal_session_event_from_chapters()

    # Use the engine exactly as in the rest of the protocol
    space = PrimeTopologicalSpace(event)
    space.compute_sheaf_laplacian()
    lam1, _ = space.compute_spectral_gap()
    h0 = space.compute_homology_dimension()
    hol = space.detect_holonomy()

    ks = {
        "dim_H0": h0,
        "lambda_1": float(lam1) if lam1 is not None else None,
        "holonomy_signature": hol,
        "sequence_length": event["meta"]["sequence_length"],
        "qualia": event["meta"]["qualia_summary"],
        "source": event["meta"]["source"],
        "note": "Baseline from sampled + synthetic restriction on the 37-chapter development manifold. Δλ₁ trend and full per-chapter will come in Phase 2/3."
    }

    print("\nBaseline Session K(S) for the 37-chapter transcript sequence:")
    for k, v in ks.items():
        print(f"  {k}: {v}")

    print("\nThis is the 'quantity (37 saves) + qualia (the linguistic essence of the")
    print("evolution) dimensioned proper' starting point. The engine (L_F via eigsh on")
    print("sparse restriction from sequence + system co-occurrence) has interpreted it.")
    print("\nNext: Phase 2 full extraction across all chapters → richer hypergraph →")
    print("updated K(S) with real trend / holonomy points from the actual 37.")
    print("=" * 72)


if __name__ == "__main__":
    main()
