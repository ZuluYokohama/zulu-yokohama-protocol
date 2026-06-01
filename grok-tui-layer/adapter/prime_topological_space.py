"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/grok-tui-layer/adapter/prime_topological_space.py
PrimeTopologicalSpace — The Sheaf Laplacian Engine (Phase 4.3 Deepened)

Now includes:
- True dim H⁰ via sparse nullspace (svds on smallest singular values)
- Basic holonomy detection on the sparse graph (cycle tracing via adjacency)
Strictly sparse. No dense matrices on hot paths.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np
from scipy.sparse import csr_matrix, identity
from scipy.sparse.linalg import eigsh, svds
from scipy.sparse.csgraph import connected_components

# Standalone execution support (Phase 4.3)
import sys
from pathlib import Path
_ADAPTER_DIR = Path(__file__).parent
if str(_ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(_ADAPTER_DIR))
from rich_prime_event_builder import RichPrimeEventBuilder


class PrimeTopologicalSpace:
    """
    The mathematical heart (Phase 4.3).
    Computes L_F, λ₁, dim H⁰, and holonomy signature from sparse data.
    """

    def __init__(self, event: Dict[str, Any]):
        self.event = event
        self.n = len(event["node_data"])
        self.restriction_map: csr_matrix = event["restriction_map_sparse"]
        self.laplacian: csr_matrix | None = None
        self.lambda_1: float | None = None
        self.dim_h0: int | None = None
        self.holonomy_signature: str = "unknown"
        self.eigenvectors: np.ndarray | None = None

    def compute_sheaf_laplacian(self) -> csr_matrix:
        """L_F = δ^T δ (strictly sparse)."""
        if self.restriction_map.shape[0] != self.n:
            self.restriction_map = self.restriction_map[:self.n, :self.n]

        delta = self.restriction_map
        self.laplacian = (delta.T @ delta).tocsr()
        self.laplacian = (self.laplacian + self.laplacian.T) / 2
        return self.laplacian

    def compute_spectral_gap(self, k: int = 4) -> Tuple[float, np.ndarray]:
        """Extract λ₁ via eigsh (smallest magnitude)."""
        if self.laplacian is None:
            self.compute_sheaf_laplacian()

        try:
            eigenvalues, eigenvectors = eigsh(
                self.laplacian,
                k=min(k, self.n-1),
                which='SM',
                tol=1e-8,
                maxiter=2000
            )
            eigenvalues = np.sort(np.abs(eigenvalues))
            self.lambda_1 = float(eigenvalues[1]) if len(eigenvalues) > 1 else 0.0
            self.eigenvectors = eigenvectors
        except Exception as e:
            print(f"[PrimeTopologicalSpace] eigsh fallback: {e}")
            self.lambda_1 = 1e-6
            self.eigenvectors = np.zeros((self.n, 2))

        return self.lambda_1, self.eigenvectors

    def compute_homology_dimension(self) -> int:
        """
        dim H⁰ ≈ dimension of kernel of L_F.
        Uses svds on the Laplacian to find near-zero singular values.
        This is the number of global sections (harmonic functions).
        """
        if self.laplacian is None:
            self.compute_sheaf_laplacian()

        try:
            # Find smallest singular values (correspond to kernel)
            u, s, vt = svds(self.laplacian, k=min(10, self.n-1), which='SM', tol=1e-8)
            # Count how many are effectively zero (within tolerance)
            zero_threshold = 1e-6 * (s.max() if len(s) > 0 else 1.0)
            self.dim_h0 = int(np.sum(s < zero_threshold))
        except Exception:
            # Fallback: connected components of the underlying graph
            adj = (self.restriction_map != 0).astype(int)
            n_components, _ = connected_components(adj, directed=False)
            self.dim_h0 = n_components

        return self.dim_h0

    def detect_holonomy(self) -> str:
        """
        Basic holonomy detection.
        Looks for non-trivial cycles in the sparse graph that would induce non-zero curvature.
        For Phase 4.3 we use a simple cycle count + consistency check on the restriction maps.
        """
        if self.restriction_map is None:
            return "unknown"

        # Build adjacency from non-zero restriction entries
        adj = (self.restriction_map != 0).astype(int).tocoo()

        # Very lightweight cycle detection: if the graph has cycles and the
        # restriction maps around those cycles are inconsistent (future: full parallel transport)
        # For now we use a heuristic: high cycle density + non-trivial kernel mismatch
        n_components, labels = connected_components(adj, directed=False)

        # Rough cycle indicator: edges >> nodes in components
        cycle_density = (adj.nnz / 2) / max(self.n, 1)

        if cycle_density > 1.5 and self.dim_h0 is not None and self.dim_h0 < n_components:
            self.holonomy_signature = f"non-trivial:cycle-density-{cycle_density:.2f}"
        else:
            self.holonomy_signature = "trivial"

        return self.holonomy_signature

    def get_cryptologic_key(self) -> Dict[str, Any]:
        """Full K(S) with H⁰ and holonomy (Phase 4.3)."""
        if self.lambda_1 is None:
            self.compute_spectral_gap()
        if self.dim_h0 is None:
            self.compute_homology_dimension()
        if self.holonomy_signature == "unknown":
            self.detect_holonomy()

        return {
            "dim_H0": self.dim_h0,
            "lambda_1": self.lambda_1,
            "holonomy_signature": self.holonomy_signature,
            "restriction_map_nnz": int(self.restriction_map.nnz),
            "laplacian_nnz": int(self.laplacian.nnz) if self.laplacian is not None else 0,
            "sparsity": 1 - (self.laplacian.nnz / (self.n ** 2)) if self.laplacian is not None else 0.0
        }


def build_prime_space_from_project(project_dir: str | Path, trigger: str = "live") -> PrimeTopologicalSpace:
    builder = RichPrimeEventBuilder(max_files=80)
    event = builder.build_from_project(project_dir, trigger=trigger)
    return PrimeTopologicalSpace(event)
