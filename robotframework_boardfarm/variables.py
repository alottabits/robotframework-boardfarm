"""Robot Framework variable file for Boardfarm configuration.

This file can be used with Robot Framework's --variablefile option to provide
Boardfarm configuration variables.

Usage:
    robot --variablefile robotframework_boardfarm/variables.py:board_name=my-board \
          --listener robotframework_boardfarm.BoardfarmListener \
          tests/

The variables can also be set via environment variables.
"""

from __future__ import annotations

import os
from typing import Any


def get_variables(
    board_name: str | None = None,
    env_config: str | None = None,
    inventory_config: str | None = None,
    skip_boot: str | None = None,
    skip_contingency_checks: str | None = None,
    save_console_logs: str | None = None,
) -> dict[str, Any]:
    """Return variables for Robot Framework.

    Variables can be overridden via:
    1. Function arguments (--variablefile variables.py:arg=value)
    2. Environment variables (BOARDFARM_BOARD_NAME, etc.)
    3. Command line (--variable BOARD_NAME:value)

    Args:
        board_name: Board name
        env_config: Environment config path
        inventory_config: Inventory config path
        skip_boot: Skip device booting ("true"/"false")
        skip_contingency_checks: Skip contingency checks ("true"/"false")
        save_console_logs: Path to save console logs

    Returns:
        Dictionary of variables for Robot Framework.
    """
    return {
        # Board configuration
        "BOARD_NAME": (
            board_name
            or os.environ.get("BOARDFARM_BOARD_NAME")
            or os.environ.get("BOARD_NAME", "")
        ),
        "ENV_CONFIG": (
            env_config
            or os.environ.get("BOARDFARM_ENV_CONFIG")
            or os.environ.get("ENV_CONFIG", "")
        ),
        "INVENTORY_CONFIG": (
            inventory_config
            or os.environ.get("BOARDFARM_INVENTORY_CONFIG")
            or os.environ.get("INVENTORY_CONFIG", "")
        ),
        # Execution options
        "SKIP_BOOT": (
            skip_boot
            or os.environ.get("BOARDFARM_SKIP_BOOT")
            or os.environ.get("SKIP_BOOT", "false")
        ),
        "SKIP_CONTINGENCY_CHECKS": (
            skip_contingency_checks
            or os.environ.get("BOARDFARM_SKIP_CONTINGENCY_CHECKS")
            or os.environ.get("SKIP_CONTINGENCY_CHECKS", "false")
        ),
        "SAVE_CONSOLE_LOGS": (
            save_console_logs
            or os.environ.get("BOARDFARM_SAVE_CONSOLE_LOGS")
            or os.environ.get("SAVE_CONSOLE_LOGS", "")
        ),
        # Common environment requirement presets (for convenience)
        "ENV_REQ_DUAL_STACK": {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": ["dual"]},
            },
        },
        "ENV_REQ_IPV4_ONLY": {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": ["ipv4"]},
            },
        },
        "ENV_REQ_IPV6_ONLY": {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": ["ipv6"]},
            },
        },
    }
