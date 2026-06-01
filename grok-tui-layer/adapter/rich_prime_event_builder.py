"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/grok-tui-layer/adapter/rich_prime_event_builder.py
RichPrimeEventBuilder — Real AST-to-Stalk Extraction Adapter (Phase 4)
──────────────────────────────────────────────────────────────────────────────────────────────
Axiomatic Dependencies:
- A3 (Semantic Alignment): Linguistic-to-codebase extraction via ContractGraph + ObligationVectors
- 5.1 (Reverse Engineering Principle): Bottom-up abstraction of geometry and topology from activity
- 5.2 (Configurational Term Series): X (raw files) → f(x) (AST walk) → M (semantic manifold)
- Previous transducer: manus-plugin-dev-session-current-4/prime_transducer.py (Task 1.2 smoke test expectations)
- MaxOp Directives: csr_matrix sparse restriction maps, prime-weighted, NPU/ARM64 friendly, 9D feature vectors

Purpose:
This is the first executable stub that moves us from structural skeletons to real geometry.
It walks actual Python source, extracts rich semantic stalks, and produces the exact
(node_data, edge_data, restriction_map_sparse) payload expected by the PrimeTopologicalSpace
and SurfaceEnclosure.

Zero-pollution rule: This file lives only in the clean seed. It will later become the adapter
that grafts the proven logic from the old transducer session.
──────────────────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import ast
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import numpy as np
from scipy.sparse import csr_matrix

# ============================================================
# 9D FEATURE VECTOR DEFINITION (Semantic Alignment v2.0)
# ============================================================

FEATURE_DIM = 9

@dataclass
class StalkFeatures:
    """
    9-dimensional feature vector per semantic unit (per A3 + 5.1).
    These become the coordinates in the Universal Tensor Space (Vol III).
    """
    node_kind: int          # 0=module, 1=class, 2=func, 3=method, 4=assign, 5=call, 6=import, 7=other
    depth: int              # AST depth (hierarchy)
    fan_in: int             # Incoming references (approximated via name resolution)
    fan_out: int            # Outgoing calls/imports
    semantic_category: int  # 0=structural, 1=behavioral, 2=data, 3=interface, 4=control
    complexity: int         # Simple cyclomatic proxy (branches + 1)
    is_public: int          # 0=private/mangled, 1=public
    has_docstring: int      # 0=no, 1=yes
    line_span: int          # Rough size proxy


def _classify_node(node: ast.AST) -> Tuple[int, int, int]:
    """Map AST node type to (kind, semantic_category, is_public)."""
    if isinstance(node, ast.Module):
        return 0, 0, 1
    if isinstance(node, ast.ClassDef):
        return 1, 0, 1 if not node.name.startswith('_') else 0
    if isinstance(node, ast.FunctionDef):
        cat = 1 if any(d.id in ('property', 'staticmethod', 'classmethod') for d in node.decorator_list if isinstance(d, ast.Name)) else 3
        return 2, cat, 1 if not node.name.startswith('_') else 0
    if isinstance(node, ast.AsyncFunctionDef):
        return 2, 1, 1 if not node.name.startswith('_') else 0
    if isinstance(node, ast.Assign):
        return 4, 2, 1
    if isinstance(node, ast.Call):
        return 5, 1, 1
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return 6, 4, 1
    return 7, 0, 1


def _extract_features(node: ast.AST, depth: int, source_lines: List[str],
                      file_imports: set[str], reverse_imports: Dict[str, int]) -> List[float]:
    """Build the 9D vector for a single AST node with real topological degree."""
    kind, category, public = _classify_node(node)
    has_doc = 0
    if hasattr(node, 'body') and node.body:
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            has_doc = 1

    complexity = 1
    if hasattr(node, 'body'):
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                complexity += 1

    line_start = getattr(node, 'lineno', 0)
    line_end = getattr(node, 'end_lineno', line_start)
    span = max(1, line_end - line_start + 1)

    # === Real fan_out / fan_in from imports (Phase 4.2) ===
    fan_out = len(file_imports) if isinstance(node, (ast.Module, ast.Import, ast.ImportFrom)) else 0

    # Crude but effective fan_in: how many other files import this module's name
    module_name = ""
    if isinstance(node, ast.Module):
        module_name = getattr(node, 'filename', "").split("/")[-1].replace(".py", "")
    fan_in = reverse_imports.get(module_name, 0) if module_name else 0

    return [
        float(kind),
        float(depth),
        float(fan_in),
        float(fan_out),
        float(category),
        float(complexity),
        float(public),
        float(has_doc),
        float(min(span, 200))
    ]


# ============================================================
# CORE BUILDER
# ============================================================

class RichPrimeEventBuilder:
    """
    Real stalk extraction engine.
    Produces the event dict consumed by PrimeTopologicalSpace and the SurfaceEnclosure.
    """

    def __init__(self, max_files: int = 50, feature_dim: int = FEATURE_DIM):
        self.max_files = max_files
        self.feature_dim = feature_dim

    def build_from_project(
        self,
        project_dir: str | Path,
        trigger: str = "unknown",
        glob: str = "**/*.py",
        max_files: int | None = None
    ) -> Dict[str, Any]:
        """
        Walk the project, parse AST, emit rich stalks + sparse restriction map skeleton.

        Returns the exact shape expected by:
        - prime_bridge.MCPToolchainGateway.encode_system_state
        - SurfaceEnclosure
        """
        root = Path(project_dir).resolve()
        py_files = sorted(root.glob(glob))[: (max_files or self.max_files)]

        node_data: List[Dict[str, Any]] = []
        edge_data: List[Dict[str, Any]] = []
        node_id = 0
        file_to_nodes: Dict[str, List[int]] = {}

        # First pass: collect import information for fan_in/fan_out
        file_imports: Dict[str, set[str]] = {}
        reverse_imports: Dict[str, int] = {}

        for f in py_files:
            try:
                source = f.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(f))
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split(".")[0])
                file_imports[str(f)] = imports
                mod_name = f.stem
                for imp in imports:
                    reverse_imports[imp] = reverse_imports.get(imp, 0) + 1
            except Exception:
                pass

        for f in py_files:
            try:
                source = f.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(f))
                self._inject_parents(tree)
                lines = source.splitlines()

                file_nodes = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign, ast.Call)):
                        feats = _extract_features(
                            node,
                            depth=self._depth(node),
                            source_lines=lines,
                            file_imports=file_imports.get(str(f), set()),
                            reverse_imports=reverse_imports
                        )
                        node_data.append({
                            "id": f"n{node_id}",
                            "kind": type(node).__name__,
                            "file": str(f.relative_to(root)),
                            "feature": feats,
                            "lineno": getattr(node, 'lineno', 0)
                        })
                        file_nodes.append(node_id)
                        node_id += 1

                file_to_nodes[str(f)] = file_nodes

                # Simple intra-file call/definition edges (future: full call graph)
                for i, n1 in enumerate(file_nodes[:-1]):
                    for n2 in file_nodes[i+1:]:
                        edge_data.append({
                            "source": f"n{n1}",
                            "target": f"n{n2}",
                            "type": "contains_or_calls",
                            "weight": 1.0
                        })

            except Exception as e:
                # Never let one bad file kill the build (continuity guard)
                node_data.append({
                    "id": f"err_{node_id}",
                    "kind": "ParseError",
                    "file": str(f.relative_to(root)),
                    "feature": [0.0] * self.feature_dim,
                    "error": str(e)[:120]
                })
                node_id += 1

        # Build sparse restriction map
        # Phase 4: Identity + intra-file containment edges (real semantic similarity later)
        # This produces a proper csr_matrix ready for L_F = delta.T @ delta in PrimeTopologicalSpace
        n = max(1, len(node_data))
        row, col, data = [], [], []

        for i in range(n):
            row.append(i)
            col.append(i)
            data.append(1.0)  # self-loop

        # Add edges within the same file as "contains" relations (stronger weight)
        for fname, nodes_in_file in file_to_nodes.items():
            for i in range(len(nodes_in_file)):
                for j in range(i + 1, len(nodes_in_file)):
                    a = nodes_in_file[i]
                    b = nodes_in_file[j]
                    row.extend([a, b])
                    col.extend([b, a])
                    data.extend([0.7, 0.7])  # symmetric containment

        restriction_map_sparse = csr_matrix((data, (row, col)), shape=(n, n))

        return {
            "trigger": trigger,
            "node_data": node_data,
            "edge_data": edge_data,
            "restriction_map_sparse": restriction_map_sparse,
            "meta": {
                "builder_version": "0.6-phase4-stub",
                "files_scanned": len(py_files),
                "nodes_extracted": len(node_data),
                "feature_dims": self.feature_dim,
                "source": "prime-crystal-grok/adapter/rich_prime_event_builder.py",
                "axiom_trace": ["A3", "5.1", "5.2", "19.4"]
            }
        }

    def _inject_parents(self, tree: ast.AST) -> None:
        """Inject .parent pointers into every node for depth calculation (standard AST preprocessing)."""
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent  # type: ignore[attr-defined]

    def _depth(self, node: ast.AST) -> int:
        d = 0
        cur = node
        while getattr(cur, 'parent', None):
            d += 1
            cur = cur.parent
        return d


# ============================================================
# STANDALONE SMOKE (for the seed)
# ============================================================

if __name__ == "__main__":
    builder = RichPrimeEventBuilder(max_files=40)
    event = builder.build_from_project(
        project_dir="prime-crystal-grok",
        trigger="phase4-adapter-smoke"
    )
    rmap = event['restriction_map_sparse']
    print("=== Phase 4 RichPrimeEventBuilder Smoke ===")
    print(f"Files scanned: {event['meta']['files_scanned']}")
    print(f"Nodes extracted: {len(event['node_data'])}")
    print(f"Edges: {len(event['edge_data'])}")
    print(f"Restriction map: {rmap.shape} nnz={rmap.nnz} sparsity={1 - (rmap.nnz / (rmap.shape[0]**2)):.4f}")
    if event['node_data']:
        print(f"Sample 9D feature (first node): {event['node_data'][0]['feature']}")
    print("Adapter stub operational. Real AST geometry now feeds csr_matrix. Ready for transducer graft.")
