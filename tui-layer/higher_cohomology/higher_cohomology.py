"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/tui-layer/higher_cohomology/higher_cohomology.py
Higher Cohomology — H¹ as Structural Voids & Technical Debt (Phase 5.1)

In the sheaf setting:
- dim H⁰ = number of globally consistent sections (what we already compute via svds).
- dim H¹ = dimension of the space of "obstructions" or voids — inconsistencies that cannot be resolved globally.

For our graph approximation of the codebase hypergraph:
- We treat the restriction map graph as a 1-complex.
- β₁ (first Betti number) ≈ number of independent cycles = "architectural voids".
- High β₁ regions or low-connectivity nodes are flagged as technical debt.

The engine can now not only measure coherence (λ₁) but actively propose mutations that reduce voids (close technical debt).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

# Standalone support
import sys
from pathlib import Path
_ADAPTER_DIR = Path(__file__).parent.parent / "adapter"
if str(_ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(_ADAPTER_DIR))
from prime_topological_space import PrimeTopologicalSpace


@dataclass
class Void:
    """A mathematically defined structural void (technical debt candidate)."""
    node_ids: List[str]
    severity: float          # normalized measure of the void (higher = worse)
    description: str
    suggested_mutation: str  # what an autonomous agent could do to close it


class HigherCohomology:
    """
    Computes H¹ (voids) on top of an existing PrimeTopologicalSpace.
    Provides actionable technical debt.
    """

    def __init__(self, space: PrimeTopologicalSpace):
        self.space = space
        self.event = space.event
        self.n = space.n
        self.rmap: csr_matrix = space.restriction_map
        self.laplacian = space.laplacian

        self.beta1: int | None = None
        self.voids: List[Void] = []

    def compute_h1_dimension(self) -> int:
        """
        Approximate dim H¹ (β₁) for the graph underlying the restriction map.

        For a graph: β₁ = E - V + C  (cycle space dimension for connected components C).
        This is the number of independent 1-cycles = "voids" in the architecture.
        """
        adj = (self.rmap != 0).astype(int)

        # Number of edges (undirected)
        e = adj.nnz // 2

        # Connected components
        n_comp, labels = connected_components(adj, directed=False)

        beta1 = e - self.n + n_comp
        self.beta1 = max(0, beta1)  # cannot be negative
        return self.beta1

    def identify_voids(self, top_k: int = 5) -> List[Void]:
        """
        Identify the most severe structural voids as technical debt.

        Heuristic (Phase 5.1):
        - Nodes with very low degree are "dangling" (missing connections).
        - Dense subgraphs with poor external connectivity are "insular" (architectural silos).
        """
        if self.beta1 is None:
            self.compute_h1_dimension()

        adj = (self.rmap != 0).astype(int).tocoo()
        degrees = np.array(adj.sum(axis=1)).flatten()

        voids = []

        # Dangling nodes (very low degree)
        low_degree = np.where(degrees < 2)[0]
        for idx in low_degree[:top_k]:
            node_id = self.event["node_data"][idx]["id"]
            voids.append(Void(
                node_ids=[node_id],
                severity=1.0 / (degrees[idx] + 0.1),
                description=f"Dangling node (degree {int(degrees[idx])}) — missing dependencies or interfaces.",
                suggested_mutation=f"Add explicit interface or dependency for {node_id}"
            ))

        # High local density but low global connectivity (insular clusters)
        # Simple proxy: nodes in small components with high internal edges
        n_comp, labels = connected_components(adj, directed=False)
        for comp in range(n_comp):
            members = np.where(labels == comp)[0]
            if len(members) > 3:
                internal_edges = sum(1 for i, j in zip(adj.row, adj.col) if labels[i] == comp and labels[j] == comp) // 2
                if internal_edges > len(members) * 1.5:  # dense inside
                    severity = internal_edges / (len(members) ** 2)
                    voids.append(Void(
                        node_ids=[self.event["node_data"][i]["id"] for i in members[:3]],
                        severity=severity,
                        description=f"Insular cluster of {len(members)} nodes with high internal coupling but low external interfaces.",
                        suggested_mutation="Introduce public interfaces or refactor to reduce hidden coupling"
                    ))

        self.voids = sorted(voids, key=lambda v: v.severity, reverse=True)[:top_k]
        return self.voids

    def suggest_debt_closing_mutations(self) -> List[str]:
        """Actionable list of mutations that would reduce H¹ (close voids)."""
        if not self.voids:
            self.identify_voids()

        suggestions = []
        for v in self.voids:
            suggestions.append(v.suggested_mutation)
        return suggestions

    def get_technical_debt_report(self) -> Dict[str, Any]:
        """Human + machine readable report of current voids."""
        if self.beta1 is None:
            self.compute_h1_dimension()
        if not self.voids:
            self.identify_voids()

        return {
            "beta1_h1_dimension": self.beta1,
            "number_of_significant_voids": len(self.voids),
            "total_technical_debt_score": sum(v.severity for v in self.voids),
            "top_voids": [
                {
                    "nodes": v.node_ids,
                    "severity": round(v.severity, 4),
                    "description": v.description,
                    "suggested_fix": v.suggested_mutation
                }
                for v in self.voids
            ]
        }
