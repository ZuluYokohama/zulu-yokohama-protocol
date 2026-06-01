"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/bipartite-router-plugin/math/prompt_topology.py
Prompt Topology Scanner — Geometric Intent Extraction (Phase 11.2 Bipartite Synthesis)

This module is the "eyes" of the Bipartite Router.

When the human types a command in the CLI, this scanner:
- Extracts semantic stalks from the prompt (treated as a high-signal "edit intent" against the current codebase manifold).
- Computes lightweight topological features:
  - β₀ proxy: fragmentation / number of isolated "islands" the edit would touch.
  - β₁ proxy: cyclicity / how many new loops or feedback paths the edit would create.
  - Δλ₁ projection: estimated impact on global coherence (H⁰ maintenance) if the edit were applied.

These three numbers are the decision features fed to router_gateway.py.

It re-uses the existing RichPrimeEventBuilder + PrimeTopologicalSpace machinery from the clean seed for consistency and zero pollution.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import re

# Import from the proven clean seed (no duplication)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "grok-tui-layer"))

from adapter.rich_prime_event_builder import RichPrimeEventBuilder
from adapter.prime_topological_space import PrimeTopologicalSpace


def extract_intent_stalks(user_prompt: str, current_event: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Treat the user's prompt as a "virtual edit" and build a lightweight stalk representation.
    In a real implementation this would do semantic embedding + retrieval against the current stalks.
    For Phase 11.2 we use a fast, deterministic proxy based on keywords + file mentions.
    """
    # Very lightweight "semantic" features from the prompt
    prompt_lower = user_prompt.lower()

    # Detect scope (how many "islands" this touches)
    file_mentions = re.findall(r'[\w\-/\\]+\.(py|ts|js|tsx|go|rs|java|cpp|h)', user_prompt)
    unique_files = set(file_mentions)

    # Detect cyclicity intent (feedback loops, new connections, refactoring)
    cyclicity_signals = len(re.findall(r'\b(refactor|connect|link|cycle|feedback|interface|bridge|router|orchestrat)\b', prompt_lower))

    # Detect coherence impact signals (global vs local)
    global_signals = len(re.findall(r'\b(global|architect|system|whole|core|foundation|invariant)\b', prompt_lower))
    local_signals = len(re.findall(r'\b(local|function|method|class|small|fix|patch)\b', prompt_lower))

    beta0_proxy = max(1, len(unique_files))          # fragmentation
    beta1_proxy = max(0, cyclicity_signals)          # new loops created
    coherence_bias = (global_signals - local_signals) / max(1, global_signals + local_signals)

    # Build a tiny synthetic event that the existing PrimeTopologicalSpace can consume
    synthetic_nodes = []
    for i, f in enumerate(list(unique_files)[:10]):  # cap for speed
        synthetic_nodes.append({
            "id": f"intent_{i}",
            "kind": "user_intent_node",
            "file": f,
            "feature": [
                5.0,                              # kind = intent
                0.0,                              # depth = 0 (high level)
                float(beta0_proxy),               # fan_in proxy
                float(beta1_proxy),               # fan_out proxy (new connections)
                3.0 if global_signals > local_signals else 2.0,  # semantic category
                1.0 + coherence_bias,             # complexity
                1.0,
                0.0,
                float(len(user_prompt) // 10)
            ]
        })

    synthetic_event = {
        "trigger": f"bipartite_intent:{user_prompt[:60]}",
        "node_data": synthetic_nodes,
        "edge_data": [],  # intent nodes are initially disconnected (high β₀)
        "restriction_map_sparse": None,  # will be built lightly below
        "meta": {
            "beta0_proxy": beta0_proxy,
            "beta1_proxy": beta1_proxy,
            "coherence_bias": coherence_bias,
            "source": "bipartite-router-plugin/math/prompt_topology.py"
        }
    }

    # Build a tiny identity + light connection matrix so the existing Space can run
    n = max(1, len(synthetic_nodes))
    from scipy.sparse import csr_matrix
    row = list(range(n)) + list(range(n-1))
    col = list(range(n)) + list(range(1, n))
    data = [1.0] * n + [0.3] * (n-1)
    synthetic_event["restriction_map_sparse"] = csr_matrix((data, (row, col)), shape=(n, n))

    return synthetic_event


def compute_prompt_topology(user_prompt: str, current_event: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    The main entry point for the Bipartite Router.

    Returns a compact topological signature of the user's intent relative to the current codebase state.
    This signature drives the hard routing decision (Local 8B vs Remote Oracle).
    """
    intent_event = extract_intent_stalks(user_prompt, current_event)

    # Reuse the battle-tested PrimeTopologicalSpace from the clean seed
    space = PrimeTopologicalSpace(intent_event)
    space.compute_sheaf_laplacian()
    lambda_1, _ = space.compute_spectral_gap(k=2)
    dim_h0 = space.compute_homology_dimension()
    holonomy = space.detect_holonomy()

    # Pull the lightweight proxies we computed during extraction
    meta = intent_event.get("meta", {})
    beta0 = meta.get("beta0_proxy", 1)
    beta1 = meta.get("beta1_proxy", 0)
    coherence_bias = meta.get("coherence_bias", 0.0)

    # Simple but effective Δλ₁ projection heuristic
    # High β₁ + low dim H0 + negative coherence_bias → strong negative projection
    projected_delta = (0.02 * coherence_bias) - (0.005 * beta1) + (0.01 * (dim_h0 / max(1, beta0)))

    signature = {
        "beta0_fragmentation": beta0,
        "beta1_cyclicity": beta1,
        "projected_delta_lambda_1": projected_delta,
        "current_dim_h0": dim_h0,
        "current_holonomy": holonomy,
        "raw_lambda_1_of_intent": lambda_1,
        "recommendation_bias": "LOCAL" if (projected_delta > -0.01 and beta0 < 4 and beta1 < 3) else "REMOTE"
    }

    return signature
