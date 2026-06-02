"""
bipartite_router_plugin — The Bipartite Metacognitive Router (Phase 11.2 Synthesis)

This plugin turns the Grok TUI / Claude Code into a true topologically-steered system.

When the human types anything, the router automatically decides:
- Local (ruthless 8B NPU path via KV Governor) or
- Remote (Claude Code Native Oracle / CodeRabbit with agent-optimized output)

The mathematics of the prompt itself now dictate the hardware and intelligence level used.
"""

from .router_gateway import get_bipartite_router, BipartiteRouter

__all__ = ["get_bipartite_router", "BipartiteRouter"]
