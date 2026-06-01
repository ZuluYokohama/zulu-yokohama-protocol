"""
integration — Wiring Patterns and Runtime Integration Notes
"""

from .grok_tui_wiring_example import (
    initialize_prime_crystal_session,
    wired_todo_write,
    wired_spawn_subagent,
    wired_run_terminal_command,
)

__all__ = [
    "initialize_prime_crystal_session",
    "wired_todo_write",
    "wired_spawn_subagent",
    "wired_run_terminal_command",
]
