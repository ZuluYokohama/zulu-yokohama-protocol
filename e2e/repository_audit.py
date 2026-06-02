"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/e2e/repository_audit.py
Step 1: Repository Audit — Zero-Pollution & MaxOp Compliance Check

This script performs the initial production readiness audit for the prime-crystal-grok
clean seed before any Dark Launch.

It enforces:
- Strict namespace isolation (no collisions with legacy Grok code)
- Dependency hygiene (only scipy + stdlib for MaxOp envelope)
- Fast cold-start initialization (< 50ms target)
- Full A4 traceability on every check
"""

from __future__ import annotations
from pathlib import Path
import time
import sys
import importlib.util
from datetime import datetime, timezone
import json

SEED_ROOT = Path(__file__).resolve().parents[1]


def audit_namespace_isolation() -> bool:
    """Ensure no polluting top-level names or legacy imports exist."""
    forbidden = {"types", "legacy", "probabilistic", "raw_llm"}
    violations = []

    for py_file in SEED_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore").lower()
        for bad in forbidden:
            if bad in content and "legacy" not in str(py_file):  # allow references in docs
                violations.append(f"{py_file.relative_to(SEED_ROOT)}: contains forbidden legacy term '{bad}'")

    if violations:
        print("[FAIL] Namespace pollution detected:")
        for v in violations:
            print(f"  - {v}")
        return False

    print("[PASS] Namespace isolation verified (zero legacy probabilistic terms in executable code).")
    return True


def audit_dependency_hygiene() -> bool:
    """Confirm only allowed dependencies for MaxOp envelope."""
    allowed = {"scipy", "numpy", "json", "pathlib", "datetime", "typing", "dataclasses", "threading"}
    violations = []

    for py_file in SEED_ROOT.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                for token in line.replace(",", " ").split():
                    if token and token not in allowed and not token.startswith(".") and token.isidentifier():
                        # Allow standard library and our own modules
                        if token not in {"sys", "os", "importlib", "contextlib", "io"}:
                            violations.append(f"{py_file.relative_to(SEED_ROOT)}: unexpected import '{token}'")

    if violations:
        print("[FAIL] Dependency hygiene violations:")
        for v in violations:
            print(f"  - {v}")
        return False

    print("[PASS] Dependency hygiene verified (only scipy + approved stdlib).")
    return True


def audit_cold_start_performance() -> bool:
    """Measure initialization time of the core engine."""
    start = time.perf_counter()

    try:
        # Simulate the critical hot path the TUI will hit on startup
        from tui-layer.persistence.ipc_bridge import create_ipc_bridge_for_grok_tui
        from tui-layer.persistence.persistent_fabric import get_persistent_fabric_for_tui

        fabric = get_persistent_fabric_for_tui(SEED_ROOT)
        bridge = create_ipc_bridge_for_grok_tui(SEED_ROOT, transport="memory_mapped")

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"[METRIC] Cold-start initialization: {elapsed_ms:.2f} ms")

        if elapsed_ms > 50:
            print(f"[WARN] Cold-start exceeded 50ms target ({elapsed_ms:.2f} ms)")
            return False

        print("[PASS] Cold-start performance within MaxOp envelope.")
        return True

    except Exception as e:
        print(f"[FAIL] Cold-start crashed: {e}")
        return False


def main():
    print("=" * 70)
    print("STEP 1: REPOSITORY AUDIT — Zero-Pollution & MaxOp Compliance")
    print(f"Seed: {SEED_ROOT}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    results = {
        "namespace_isolation": audit_namespace_isolation(),
        "dependency_hygiene": audit_dependency_hygiene(),
        "cold_start_performance": audit_cold_start_performance(),
    }

    all_passed = all(results.values())

    bundle = {
        "manifest": {
            "type": "PHASE_5_2_REPOSITORY_AUDIT",
            "version": "0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "axioms": ["20.3", "Forge_Law_5", "A4"],
            "target": "Production readiness gate before Dark Launch"
        },
        "results": results,
        "verdict": "PASS" if all_passed else "FAIL"
    }

    bundle_path = SEED_ROOT / "evidence" / "e2e" / "REPOSITORY_AUDIT_RESULT.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)

    print(f"\nAudit complete. Evidence: {bundle_path}")
    print(f"VERDICT: {bundle['verdict']}")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
