"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/grok-tui-layer/integration/grok_tui_main_shim.py
Grok TUI Main Shim — The Binary Entry Point Replacement (Phase 5.2)

This is the drop-in replacement for the legacy Grok TUI `main()`.

It:
- Initializes the TermSeries + PrimeTopologicalSpace
- Wires the Seamless Override interceptor around the core event loop
- Forces every terminal output and tool execution through the csr_matrix evaluation
- Deprecates the raw probabilistic generation path

In production this file (or its compiled equivalent) becomes the actual `grok` binary entry point
when the Prime Crystal protocol is enabled for a session.
"""

from __future__ import annotations
from pathlib import Path
import sys
import json
from datetime import datetime, timezone

# Clean seed imports (in real deployment these become part of the Grok package)
from ..persistence.ipc_bridge import create_ipc_bridge_for_grok_tui
from ..persistence.persistent_fabric import get_persistent_fabric_for_tui
from ..adapter.prime_topological_space import PrimeTopologicalSpace
from ..integration.transducer_graft import TransducerGraft


class GrokTUIPrimeCrystalShim:
    """
    The actual runtime shim that the Grok TUI process boots into.
    """

    def __init__(self, seed_root: Path):
        self.seed_root = Path(seed_root).resolve()
        print(f"[GrokTUIPrimeCrystalShim] Booting with Prime Crystal protocol")
        print(f"    Seed: {self.seed_root}")

        # 1. Boot the persistent fabric (continuous K(S))
        self.fabric = get_persistent_fabric_for_tui(self.seed_root)

        # 2. Create the IPC bridge (hot K(S) for the TUI process)
        self.bridge = create_ipc_bridge_for_grok_tui(self.seed_root, transport="memory_mapped")

        # 3. Prepare the grafted builder (real AST stalks)
        self.graft = TransducerGraft(self.seed_root)

        print("[GrokTUIPrimeCrystalShim] Persistent Fabric + IPC Bridge online")
        print(f"    Baseline λ₁: {self.fabric.get_current_ks().get('lambda_1', 0):.6f}")

    def on_user_input(self, user_prompt: str, context: dict) -> dict:
        """
        This replaces the legacy "generate response" path.

        Every user message is now a term in the continuous series.
        """
        trigger = f"tui:user_input:{datetime.now(timezone.utc).isoformat()}"

        # The Seamless Override lives here
        result = self.bridge.evolve(trigger, {"type": "user_prompt", "content": user_prompt})

        if not result["allowed"]:
            # The solver has already self-corrected inside the bridge
            print(f"[Seamless Override] Blocked probabilistic output. Reason: {result.get('blocked_reason')}")
            # Return the mathematically valid projection instead
            return {
                "type": "corrected",
                "content": self._generate_corrected_response(user_prompt, result),
                "ks": result["current_ks"]
            }

        # Normal path (still goes through topological evaluation in real impl)
        return {
            "type": "normal",
            "content": f"[Topologically steered] {user_prompt}",
            "ks": result["current_ks"]
        }

    def on_tool_call(self, tool_name: str, args: dict) -> dict:
        """
        Every tool execution (file write, terminal, subagent, etc.) must pass the gate.
        """
        trigger = f"tui:tool:{tool_name}"

        result = self.bridge.evolve(trigger, {"tool": tool_name, "args": args})

        if not result["allowed"]:
            print(f"[Seamless Override] Tool call blocked: {tool_name}")
            return {"status": "blocked", "reason": result.get("blocked_reason"), "ks": result.get("current_ks")}

        # In real TUI this is where we would actually execute the tool
        return {"status": "executed", "ks": result.get("current_ks")}

    def _generate_corrected_response(self, prompt: str, bridge_result: dict) -> str:
        """The solver's mathematically valid projection (instead of raw LLM output)."""
        return (
            f"[Prime Crystal Correction]\n"
            f"Original intent: {prompt}\n"
            f"Geometric issue: {bridge_result.get('blocked_reason')}\n"
            f"Corrected action: The solver has adjusted the proposed change to preserve coherence.\n"
            f"Current K(S): λ₁={bridge_result['current_ks'].get('lambda_1', 0):.6f}"
        )

    def shutdown(self):
        """Called on TUI exit. Guarantees final evidence deposit."""
        self.bridge.stop()
        print("[GrokTUIPrimeCrystalShim] Clean shutdown. Final K(S) persisted.")


# The actual entry point the Grok binary would call
def grok_tui_main(seed_root: Path | None = None):
    """
    Drop-in replacement for the legacy Grok TUI main().

    When the user enables Prime Crystal mode (or the protocol detects the clean seed),
    this becomes the real main().
    """
    if seed_root is None:
        # In real deployment this would be determined by environment or config
        seed_root = Path(__file__).resolve().parents[4] / "prime-crystal-grok"

    shim = GrokTUIPrimeCrystalShim(seed_root)

    print("\n[Grok TUI] Prime Crystal mode active. Legacy probabilistic path deprecated.")
    print("All terminal output and tool execution now passes through the Reality Bridge.\n")

    # Simulated event loop (in real TUI this is the actual input loop)
    try:
        while True:
            user_input = input("grok> ").strip()
            if user_input.lower() in ("exit", "quit"):
                break

            response = shim.on_user_input(user_input, {})
            print(response["content"])
            print(f"  [K(S)] λ₁={response['ks'].get('lambda_1', 0):.6f}")

    except KeyboardInterrupt:
        pass
    finally:
        shim.shutdown()


if __name__ == "__main__":
    grok_tui_main()
