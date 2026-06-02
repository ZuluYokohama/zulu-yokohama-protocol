"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/edge_compute/__init__.py
Edge Compute Namespace – Phase 11: ARM64 NPU Deployment Refactor

Axiomatic Dependencies:
- MaxOp Hardware Axioms (Operational Blueprint for 8B models on 6GB ARM64+NPU)
- Phase 3 sparse csr_matrix invariants
- Phase 4/8/9 H⁰/H¹/H²/H³ preservation
- Volume IV Computational Architecture (NPU kernel offload)
- Volume VI Integration Layer (edge deployment)

Purpose: All 6GB-constrained, NPU-accelerated topological logic lives here.
Zero pollution of the core tui-layer/ proven in previous phases.
"""

__version__ = "0.1.0-phase11"
__hardware_target__ = "8-core ARM64 + NPU (≤6GB VRAM)"
