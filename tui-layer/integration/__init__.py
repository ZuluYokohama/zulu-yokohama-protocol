"""
integration — Wiring Patterns and Runtime Integration Notes
"""

from .tui_wiring_example import (
    initialize_prime_crystal_session,
    wired_run_terminal_command,
    wired_spawn_subagent,
    wired_todo_write,
)

__all__ = [
    "initialize_prime_crystal_session",
    "wired_run_terminal_command",
    "wired_spawn_subagent",
    "wired_todo_write",
]
