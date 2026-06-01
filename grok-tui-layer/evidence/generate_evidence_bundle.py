"""
WORMHOLE-PATH1 | OMEGA-CLASS | prime-crystal-grok/grok-tui-layer/evidence/generate_evidence_bundle.py
Evidence Bundle Generator — Living Logbook as Sheaf Data (Forge Law 7 + Axiom 19.4)
──────────────────────────────────────────────────────────────────────────────────────────────
Axioms: 19.4 (Term-Series Execution logging), 6.1 (Topological Verification),
        20.3 (Integration Protocol), 15.2 (Yield Extraction)
Forge Origin: "Every scan, every edit, every test gets a timestamped entry against the project's fingerprint"
Output: Timestamped JSON bundles in the style of the original OMEGA evidence (but now native 19.4 + K(S) trajectory)
Purpose: Called by the Grok agent at end of significant term sequences (or on user "continue")
         to deposit the complete, queryable record of the diffusion path.
──────────────────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import json

from ..state.term_series import ActiveTermSeries


def generate_evidence_bundle(series: ActiveTermSeries, output_dir: str | Path = "prime-crystal-grok/evidence") -> Path:
    """
    Produces a full evidence bundle for the current ActiveTermSeries.

    This is the direct realization of the "Logbook" law and 19.4 axiom trace requirement.
    Every significant session or "continue" sequence must call this before the next major term.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    bundle_name = f"PC_GROK_EVIDENCE_{series.session_id}_{ts}.json"
    bundle_path = Path(output_dir) / bundle_name

    bundle = {
        "manifest": {
            "type": "PRIME_CRYSTAL_GROK_EVIDENCE_BUNDLE",
            "version": "0.1",
            "session_id": series.session_id,
            "generated_at": ts,
            "axioms": ["5.2", "19.4", "20.3", "6.1", "15.2", "Forge_Law_7"],
            "protocol": "Grok Prime Crystal Operating Protocol v0.1"
        },
        "baseline_k": series.start_k.to_dict(),
        "final_k": series.current_k().to_dict(),
        "trajectory": {
            "lambda_1_series": [k.lambda_1 for k in series.ks_history.keys],
            "deltas": series.ks_history.deltas,
            "trend": series.ks_history.trend(),
            "converged": series.ks_history.is_converged(series.convergence_threshold)
        },
        "terms_executed": [
            {
                "index": t.index,
                "trigger": t.trigger,
                "delta_lambda_1": t.delta_lambda_1,
                "gate_passed": t.gate_passed,
                "a4_attempted": t.a4_attempted,
                "a4_success": t.a4_success,
                "axiom_trace": t.axiom_trace,
                "restriction_map": {
                    "shape": t.restriction_map_shape,
                    "nnz": t.restriction_map_nnz
                } if t.restriction_map_shape else None
            }
            for t in series.terms
        ],
        "a4_repair_log": [
            {
                "term_index": e.term_index,
                "before": e.before.to_dict(),
                "after": e.after.to_dict(),
                "repair_actions": e.repair_actions,
                "success": e.success,
                "timestamp": e.timestamp
            }
            for e in series.a4_log.attempts
        ],
        "guarded_surfaces": sorted(set(t.trigger.split(":")[0] for t in series.terms)),
        "value_function_constraints": series.value_function,
        "max_terms": series.max_terms,
        "convergence_threshold": series.convergence_threshold
    }

    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print(f"[EVIDENCE] Bundle deposited: {bundle_path}")
    return bundle_path


def quick_bundle_from_current_session(series: ActiveTermSeries) -> Path:
    """Convenience wrapper used by the agent when the user says 'continue'."""
    return generate_evidence_bundle(series)


if __name__ == "__main__":
    # Minimal self-test
    from ..state.term_series import ActiveTermSeries, CryptologicKey

    demo_series = ActiveTermSeries(
        session_id="demo-001",
        start_k=CryptologicKey(12, 17.08, "trivial")
    )
    # Simulate a couple of terms
    demo_series.ks_history.append(CryptologicKey(13, 17.31, "trivial"), +0.23)
    demo_series.ks_history.append(CryptologicKey(14, 17.29, "trivial"), -0.02)

    path = quick_bundle_from_current_session(demo_series)
    print(f"Self-test bundle written to {path}")
