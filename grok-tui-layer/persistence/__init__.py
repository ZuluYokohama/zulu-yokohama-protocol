"""
persistence — The Persistent Fabric (TUI Overlay) for continuous conscious operation.

Maintains K(S) across Grok TUI "turns" / prompts.
Every new action evolves the previous manifold state.
"""

from .persistent_fabric import PersistentFabric, PersistentSurfaceEnclosure

__all__ = ["PersistentFabric", "PersistentSurfaceEnclosure"]
