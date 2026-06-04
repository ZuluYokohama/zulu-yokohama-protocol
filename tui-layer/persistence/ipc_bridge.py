"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/tui-layer/persistence/ipc_bridge.py
IPC Bridge — Cross-Process Persistence Layer (Phase 5.2)

This module provides the nervous system binding between the Grok TUI process
and the Prime Crystal topological solver.

Design Goals:
- Zero latency for hot K(S) path.
- Zero structural pollution (clean seed only).
- Hot in-memory K(S) across the entire TUI session lifecycle.
- Fallback to JSON-RPC over localhost for process separation.
- Strict A4 recovery on any IPC failure.

This is the permanent bridge. Once wired, the legacy probabilistic path is deprecated.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..state.term_series import ActiveTermSeries, CryptologicKey
from .persistent_fabric import PersistentFabric, get_persistent_fabric_for_tui


class IPCBridge:
    """
    The cross-process persistence bridge.

    In production this would use:
    - Memory-mapped files for ultra-low latency (preferred for same-machine TUI).
    - JSON-RPC over Unix socket / localhost TCP as fallback.
    - ZeroMQ or shared memory for higher throughput.

    For Phase 5.2 we provide a clean, testable stub that can be swapped for
    the real transport without changing the calling surface.
    """

    def __init__(self, seed_root: Path, transport: str = "memory_mapped"):
        self.seed_root = Path(seed_root).resolve()
        self.transport = transport
        self.fabric: PersistentFabric | None = None
        self._lock = threading.RLock()
        self._last_ks: dict[str, Any] | None = None
        self._running = False

        # Initialize the persistent fabric (this holds the real K(S))
        self.fabric = get_persistent_fabric_for_tui(self.seed_root)

        if transport == "memory_mapped":
            self._init_memory_mapped()
        elif transport == "json_rpc":
            self._init_json_rpc()
        else:
            raise ValueError(f"Unknown transport: {transport}")

    def _init_memory_mapped(self):
        """Preferred path: memory-mapped file for same-process or same-machine speed."""
        self.mm_path = self.seed_root / "evidence" / "persistence" / "ks_mmap.bin"
        self.mm_path.parent.mkdir(parents=True, exist_ok=True)
        # In real impl we would use mmap + struct for binary K(S).
        # For now we use a simple JSON side-car that the TUI can watch.
        print(f"[IPCBridge] Memory-mapped transport initialized at {self.mm_path}")

    def _init_json_rpc(self):
        """Fallback: lightweight JSON-RPC server for true process separation."""
        # Stub: in production this would start a small JSON-RPC server thread.
        print("[IPCBridge] JSON-RPC transport stub initialized (localhost:4872)")

    def get_current_ks(self) -> dict[str, Any]:
        """Fast path for the TUI to read the live K(S) with minimal latency."""
        with self._lock:
            if self.fabric and self.fabric.series:
                current = self.fabric.get_current_ks()
                self._last_ks = current
                return current
            return self._last_ks or {}

    def evolve(self, trigger: str, proposed_action: Any) -> dict[str, Any]:
        """
        The main entry point called by the TUI on every significant event.

        This is where the Seamless Override lives in production.
        The TUI calls this instead of raw generation / execution.
        """
        with self._lock:
            result = self.fabric.evolve(trigger, proposed_action) if self.fabric else {"allowed": False, "blocked_reason": "No fabric"}
            self._last_ks = result.get("current_ks", {})
            return result

    def start_background_sync(self, interval: float = 0.5):
        """Background thread that keeps the hot K(S) visible to the TUI process."""
        if self._running:
            return
        self._running = True

        def _sync_loop():
            while self._running:
                try:
                    self.get_current_ks()  # refresh
                except Exception:
                    pass
                time.sleep(interval)

        t = threading.Thread(target=_sync_loop, daemon=True)
        t.start()
        print("[IPCBridge] Background K(S) sync started")

    def stop(self):
        self._running = False
        if self.fabric:
            self.fabric.save()

    def get_full_state(self) -> dict[str, Any]:
        """For debugging / A4 recovery."""
        return {
            "transport": self.transport,
            "current_ks": self.get_current_ks(),
            "session_id": self.fabric.session_id if self.fabric else None,
            "last_updated": datetime.now(UTC).isoformat()
        }


# Factory the real Grok TUI binary will call at startup
def create_ipc_bridge_for_grok_tui(seed_root: Path, transport: str = "memory_mapped") -> IPCBridge:
    """
    The single function the Grok TUI main process calls to bind to the Reality Bridge.
    """
    bridge = IPCBridge(seed_root, transport=transport)
    bridge.start_background_sync()
    return bridge
