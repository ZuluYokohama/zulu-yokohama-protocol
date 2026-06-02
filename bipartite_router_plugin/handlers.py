"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/bipartite_router_plugin/handlers.py
Claude Code Plugin Handlers for the Bipartite Router (Phase 11.2)

These are the concrete entry points registered in .claude-plugin/plugin.json.
They are deliberately tiny — they exist only to satisfy the plugin contract and immediately
hand off to the real `router_gateway.py`.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from .router_gateway import get_bipartite_router


def route_user_prompt(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """UserPromptSubmit hook — the primary decision point for every human message."""
    prompt = args.get("prompt", "") or args.get("text", "")
    seed_root = Path(context.get("workspace", "."))

    router = get_bipartite_router(seed_root)
    decision = router.route(prompt, context)

    return {
        "routed_to": decision["route"],
        "reason": decision["reason"],
        "action": decision["action"],
        "topology": decision["topology"]
    }


def handle_coderabbit_review(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Intercepts the /coderabbit:review command and forces it through the topological router."""
    seed_root = Path(context.get("workspace", "."))
    router = get_bipartite_router(seed_root)

    # The router itself will decide whether this review can be satisfied locally
    # or must go to the real remote Oracle (and will perform the zero-VRAM context swap).
    decision = router.route(f"/coderabbit:review {args.get('diff', args.get('changes', ''))[:200]}", context)

    if decision["route"] == "LOCAL":
        return {
            "status": "handled_locally",
            "message": "Review satisfied by local topological analysis (no remote call needed).",
            "topology": decision["topology"]
        }
    else:
        # Let the real oracle handler (claude_code_oracle.py) do the heavy lifting
        from edge_compute.claude_code_oracle import handle_coderabbit_review as real_oracle
        return real_oracle(args, context)


def pre_tool_router(tool_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """PreToolUse hook — every mutation is first classified geometrically."""
    seed_root = Path(context.get("workspace", "."))
    router = get_bipartite_router(seed_root)

    decision = router.route(f"tool:{tool_name} {str(args)[:100]}", context)

    if decision["route"] == "LOCAL":
        # Safe local mutation — proceed with stripped context
        return {"proceed": True, "routed_to": "LOCAL", "context_stripped": True}
    else:
        # This mutation has macro-architectural weight — force it through the Oracle path
        return {
            "proceed": False,
            "routed_to": "REMOTE",
            "reason": decision["reason"],
            "required_action": "Invoke /coderabbit:review with full topological context first"
        }
