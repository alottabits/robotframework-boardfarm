"""Command-line interface for Robot Framework with Boardfarm integration.

This module provides the `bfrobot` command that wraps Robot Framework
with Boardfarm options, providing a consistent CLI experience similar
to pytest-boardfarm and the boardfarm CLI.

Usage:
    bfrobot --board-name my-board --env-config env.json \
            --inventory-config inv.json robot/tests/

This is equivalent to running pytest with boardfarm options:
    pytest --board-name my-board --env-config env.json \
           --inventory-config inv.json tests/
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

from robot import run_cli

if TYPE_CHECKING:
    from collections.abc import Sequence


def create_boardfarm_parser() -> argparse.ArgumentParser:
    """Create argument parser for boardfarm options.

    Returns:
        ArgumentParser with boardfarm-specific options.
    """
    parser = argparse.ArgumentParser(
        prog="bfrobot",
        description="Robot Framework with Boardfarm integration",
        epilog="""
Examples:
  bfrobot --board-name my-board --env-config env.json --inventory-config inv.json tests/
  bfrobot --board-name my-board --env-config env.json --inventory-config inv.json --skip-boot tests/
  bfrobot --board-name my-board --env-config env.json --inventory-config inv.json --outputdir results tests/

All standard Robot Framework options are also supported (e.g., --outputdir, --include, --exclude).
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Allow unknown args to pass through to robot
        add_help=False,
    )

    # Boardfarm options group
    bf_group = parser.add_argument_group("Boardfarm Options")

    bf_group.add_argument(
        "--board-name",
        type=str,
        required=True,
        help="Name of the board to use",
    )
    bf_group.add_argument(
        "--env-config",
        type=str,
        required=True,
        help="Path to environment JSON config file",
    )
    bf_group.add_argument(
        "--inventory-config",
        type=str,
        required=True,
        help="Path to inventory JSON config file",
    )
    bf_group.add_argument(
        "--skip-boot",
        action="store_true",
        help="Skip device booting, use devices as they are",
    )
    bf_group.add_argument(
        "--skip-contingency-checks",
        action="store_true",
        help="Skip contingency checks while running tests",
    )
    bf_group.add_argument(
        "--save-console-logs",
        type=str,
        default="",
        help="Save console logs at the given location",
    )
    bf_group.add_argument(
        "--legacy",
        action="store_true",
        help="Enable legacy device access mode (devices.<name>)",
    )
    bf_group.add_argument(
        "--ignore-devices",
        type=str,
        default="",
        help="Comma-separated list of devices to ignore",
    )

    # Help option
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message and exit",
    )

    return parser


def build_listener_arg(bf_args: argparse.Namespace) -> str:
    """Build the listener argument string from parsed boardfarm options.

    Args:
        bf_args: Parsed boardfarm arguments

    Returns:
        Listener argument string for robot --listener option
    """
    parts = ["robotframework_boardfarm.BoardfarmListener"]

    # Add all boardfarm options
    parts.append(f"board_name={bf_args.board_name}")
    parts.append(f"env_config={bf_args.env_config}")
    parts.append(f"inventory_config={bf_args.inventory_config}")

    if bf_args.skip_boot:
        parts.append("skip_boot=true")
    if bf_args.skip_contingency_checks:
        parts.append("skip_contingency_checks=true")
    if bf_args.save_console_logs:
        parts.append(f"save_console_logs={bf_args.save_console_logs}")
    if bf_args.legacy:
        parts.append("legacy=true")
    if bf_args.ignore_devices:
        parts.append(f"ignore_devices={bf_args.ignore_devices}")

    return ":".join(parts)


def main(args: Sequence[str] | None = None) -> int:
    """Main entry point for bfrobot command.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code from robot execution
    """
    if args is None:
        args = sys.argv[1:]

    # Parse known boardfarm args, pass rest to robot
    parser = create_boardfarm_parser()
    bf_args, robot_args = parser.parse_known_args(args)

    # Handle help
    if bf_args.help:
        parser.print_help()
        print("\n--- Robot Framework Options ---")
        print("Run 'robot --help' to see all Robot Framework options.")
        return 0

    # Build listener argument
    listener_arg = build_listener_arg(bf_args)

    # Build complete robot command
    robot_command = [
        "--listener", listener_arg,
        *robot_args,
    ]

    # Print what we're running (for debugging)
    print(f"Running: robot {' '.join(robot_command)}")
    print()

    # Run robot
    return run_cli(robot_command, exit=False)


if __name__ == "__main__":
    sys.exit(main())
