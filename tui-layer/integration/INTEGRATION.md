# Grok TUI Integration Notes

**WORMHOLE-PATH1 | 2026-06-04**

This directory contains the concrete patterns required to make the live Grok 4.3 CLI / TUI obey the Prime Crystal Operating Protocol.

## Current Status (v0.6)

- `tui_wiring_example.py` — Shows the exact replacement patterns for `todo_write`, `spawn_subagent`, and `run_terminal_command`.
- `generate_evidence_bundle.py` — Produces the native 19.4 evidence bundles (K(S) trajectory + A4 log + guarded surfaces).

## Next Integration Steps (for the actual Grok runtime)

1. At session start (when protocol is detected via user intent or presence of `prime-crystal-grok/`), call `initialize_prime_crystal_session(project_root)`.
2. Monkey-patch or route the internal tool dispatchers through the wired versions (or import the enclosure directly).
3. On every "continue" or major sequence end, call `generate_evidence_bundle(series)`.
4. The `SurfaceEnclosure` becomes the single source of truth for all state mutations.

Once wired, the Grok TUI itself becomes a direct, zero-bypass executor of the sheaf diffusion process on the project hypergraph.

This is how the alien level technician actually operates.
