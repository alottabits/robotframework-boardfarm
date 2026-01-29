"""Robot Framework listener for Boardfarm integration.

This module provides the BoardfarmListener class that manages the lifecycle
of Boardfarm devices during Robot Framework test execution.

The listener handles:
- Device deployment at suite start
- Device release at suite end
- Environment requirement validation at test start
- Contingency checks before test execution
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.config
import sys
from argparse import Namespace
from typing import TYPE_CHECKING, Any

from boardfarm3.lib.boardfarm_config import (
    BoardfarmConfig,
    get_inventory_config,
    get_json,
    parse_boardfarm_config,
)
from boardfarm3.lib.device_manager import DeviceManager
from boardfarm3.main import get_plugin_manager

from robotframework_boardfarm.exceptions import (
    BoardfarmListenerError,
    DeviceNotInitializedError,
    EnvironmentMismatchError,
)
from robotframework_boardfarm.utils import is_env_matching

if TYPE_CHECKING:
    from pluggy import PluginManager
    from robot.running import TestCase, TestSuite
    from robot.result import TestCase as ResultCase
    from robot.result import TestSuite as ResultSuite


# Global state for accessing listener from library
_LISTENER_INSTANCE: BoardfarmListener | None = None

# Boolean options that are flags (action="store_true" in argparse)
_BOOLEAN_OPTIONS = frozenset({
    "skip_boot",
    "skip_contingency_checks",
    "legacy",
})

# Default values for boardfarm options
_DEFAULT_OPTIONS: dict[str, Any] = {
    "board_name": "",
    "env_config": "",
    "inventory_config": "",
    "skip_boot": False,
    "skip_contingency_checks": False,
    "save_console_logs": "",
    "legacy": False,
    "ignore_devices": "",
}


def get_listener() -> BoardfarmListener:
    """Get the current listener instance.

    Returns:
        The active BoardfarmListener instance.

    Raises:
        BoardfarmListenerError: If no listener is active.
    """
    if _LISTENER_INSTANCE is None:
        msg = "BoardfarmListener is not initialized. Ensure listener is registered."
        raise BoardfarmListenerError(msg)
    return _LISTENER_INSTANCE


def _normalize_option_name(name: str) -> str:
    """Normalize option name to underscore format.

    Converts dashes to underscores for consistent internal handling.
    Both 'skip-boot' and 'skip_boot' become 'skip_boot'.

    Args:
        name: Option name (may contain dashes or underscores)

    Returns:
        Normalized option name with underscores
    """
    return name.replace("-", "_")


def _parse_option_value(name: str, value: str) -> Any:
    """Parse option value based on option type.

    Boolean options (flags) are parsed as True/False.
    Other options are returned as-is.

    Args:
        name: Normalized option name
        value: String value from listener argument

    Returns:
        Parsed value (bool for flags, str for others)
    """
    if name in _BOOLEAN_OPTIONS:
        # Handle various boolean representations
        return value.lower() in ("true", "1", "yes", "")
    return value


class BoardfarmListener:
    """Robot Framework listener for Boardfarm device lifecycle management.

    This listener integrates with Robot Framework's test execution lifecycle
    to deploy and release Boardfarm devices automatically.

    All boardfarm command-line options can be passed as listener arguments,
    using either underscores or dashes (e.g., skip_boot or skip-boot).

    Common Options:
        board_name: Name of the board to use (required)
        env_config: Path to environment JSON config (required)
        inventory_config: Path to inventory JSON config (required)
        skip_boot: Skip device booting (flag)
        skip_contingency_checks: Skip contingency checks (flag)
        save_console_logs: Path to save console logs
        legacy: Enable legacy device access mode (flag)
        ignore_devices: Comma-separated list of devices to ignore

    Examples:
        # Basic usage
        robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=my-board:env_config=env.json:inventory_config=inv.json"

        # With skip-boot flag (use underscore in listener args)
        robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=my-board:env_config=env.json:inventory_config=inv.json:\
skip_boot=true"

        # Multiple options
        robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=my-board:env_config=env.json:inventory_config=inv.json:\
skip_boot=true:save_console_logs=./logs:ignore_devices=wan,lan"
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, **kwargs: str) -> None:
        """Initialize boardfarm listener with flexible options.

        All boardfarm options can be passed as keyword arguments.
        Option names can use underscores or dashes (normalized internally).

        Args:
            **kwargs: Boardfarm options as key=value pairs.
                      Boolean flags accept: true/false/1/0/yes/no
        """
        global _LISTENER_INSTANCE  # noqa: PLW0603
        _LISTENER_INSTANCE = self

        # Start with defaults and merge provided options
        self._options: dict[str, Any] = dict(_DEFAULT_OPTIONS)

        for key, value in kwargs.items():
            normalized_key = _normalize_option_name(key)
            self._options[normalized_key] = _parse_option_value(normalized_key, value)

        self._plugin_manager: PluginManager = get_plugin_manager()
        self._device_manager: DeviceManager | None = None
        self._boardfarm_config: BoardfarmConfig | None = None
        self._deployment_data: dict[str, Any] = {}
        self._teardown_data: dict[str, Any] = {}
        self._is_deployed = False

        self._logger = logging.getLogger("boardfarm.robotframework")

        # Log parsed options for debugging
        self._logger.debug("BoardfarmListener initialized with options: %s", self._options)

        # Configure logging
        self._configure_logging()

    def _configure_logging(self) -> None:
        """Configure logging for the listener."""
        try:
            from boardfarm3.configs import LOGGING_CONFIG

            logging.config.dictConfig(LOGGING_CONFIG)
        except ImportError:
            # Use basic configuration if boardfarm config not available
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

    @property
    def device_manager(self) -> DeviceManager:
        """Return device manager instance.

        Raises:
            DeviceNotInitializedError: If devices haven't been deployed.
        """
        if self._device_manager is None:
            msg = "Device manager not initialized. Devices not yet deployed."
            raise DeviceNotInitializedError(msg)
        return self._device_manager

    @property
    def boardfarm_config(self) -> BoardfarmConfig:
        """Return boardfarm config instance.

        Raises:
            DeviceNotInitializedError: If config hasn't been parsed.
        """
        if self._boardfarm_config is None:
            msg = "Boardfarm config not initialized."
            raise DeviceNotInitializedError(msg)
        return self._boardfarm_config

    @property
    def cmdline_args(self) -> Namespace:
        """Return command line arguments as Namespace.

        Creates a Namespace object compatible with boardfarm hooks.
        All options from self._options are included.
        """
        return Namespace(**self._options)

    def get_option(self, name: str, default: Any = None) -> Any:
        """Get a boardfarm option value.

        Args:
            name: Option name (can use dashes or underscores)
            default: Default value if option not set

        Returns:
            Option value or default
        """
        normalized = _normalize_option_name(name)
        return self._options.get(normalized, default)

    def start_suite(self, data: TestSuite, result: ResultSuite) -> None:
        """Deploy boardfarm devices at suite start.

        Only deploys for the root suite (top-level) to ensure devices
        are deployed once for the entire test run.

        Args:
            data: Test suite data from Robot Framework
            result: Test suite result object
        """
        # Only deploy at root suite level
        if data.parent is not None:
            return

        self._logger.info("Starting Boardfarm deployment for suite: %s", data.name)

        try:
            self._deploy_devices()
            self._deployment_data["status"] = "success"
            result.metadata["Boardfarm Status"] = "Deployed"
            result.metadata["Board Name"] = self._options["board_name"]
        except Exception as e:
            self._deployment_data["status"] = "failed"
            self._deployment_data["exception"] = str(e)
            result.metadata["Boardfarm Status"] = f"Failed: {e}"
            self._logger.exception("Failed to deploy boardfarm devices")
            raise

    def end_suite(self, data: TestSuite, result: ResultSuite) -> None:
        """Release boardfarm devices at suite end.

        Only releases for the root suite (top-level).

        Args:
            data: Test suite data from Robot Framework
            result: Test suite result object
        """
        # Only release at root suite level
        if data.parent is not None:
            return

        self._logger.info("Releasing Boardfarm devices for suite: %s", data.name)

        try:
            self._release_devices()
            self._teardown_data["status"] = "success"
        except Exception as e:
            self._teardown_data["status"] = "failed"
            self._teardown_data["exception"] = str(e)
            self._logger.exception("Failed to release boardfarm devices")
            # Don't re-raise to allow test results to be recorded

    def start_test(self, data: TestCase, result: ResultCase) -> None:
        """Validate environment requirements before test execution.

        Args:
            data: Test case data from Robot Framework
            result: Test case result object
        """
        if self._options["skip_contingency_checks"]:
            return

        # Parse env_req from tags
        env_req = self._parse_env_req_tags(list(data.tags))

        if env_req:
            try:
                self._validate_env_requirement(env_req)
                self._run_contingency_check(env_req)
            except EnvironmentMismatchError as e:
                from robot.api import SkipExecution

                raise SkipExecution(str(e)) from e

    def end_test(self, data: TestCase, result: ResultCase) -> None:
        """Cleanup after test execution.

        Args:
            data: Test case data from Robot Framework
            result: Test case result object
        """
        # Future: capture logs, cleanup context, etc.
        pass

    def _deploy_devices(self) -> None:
        """Deploy boardfarm devices to the environment."""
        if self._is_deployed:
            self._logger.debug("Devices already deployed, skipping")
            return

        # Validate required configuration
        board_name = self._options["board_name"]
        inventory_config_path = self._options["inventory_config"]
        env_config_path = self._options["env_config"]

        if not board_name:
            msg = "board_name is required but not provided"
            raise BoardfarmListenerError(msg)
        if not inventory_config_path:
            msg = "inventory_config is required but not provided"
            raise BoardfarmListenerError(msg)
        if not env_config_path:
            msg = "env_config is required but not provided"
            raise BoardfarmListenerError(msg)

        self._logger.info("Deploying devices for board: %s", board_name)

        # Configure boardfarm
        self._plugin_manager.hook.boardfarm_configure(
            cmdline_args=self.cmdline_args,
            plugin_manager=self._plugin_manager,
        )

        # Reserve devices
        inventory_config = self._plugin_manager.hook.boardfarm_reserve_devices(
            cmdline_args=self.cmdline_args,
            plugin_manager=self._plugin_manager,
        )

        # If no inventory returned from hook, load directly
        if inventory_config is None:
            inventory_config = get_inventory_config(
                board_name,
                inventory_config_path,
            )

        # Parse boardfarm config
        env_config = get_json(env_config_path)
        self._boardfarm_config = self._plugin_manager.hook.boardfarm_parse_config(
            cmdline_args=self.cmdline_args,
            inventory_config=inventory_config,
            env_config=env_config,
        )

        # If no config returned from hook, parse directly
        if self._boardfarm_config is None:
            self._boardfarm_config = parse_boardfarm_config(
                inventory_config,
                env_config,
            )

        # Register devices
        self._device_manager = self._plugin_manager.hook.boardfarm_register_devices(
            config=self._boardfarm_config,
            cmdline_args=self.cmdline_args,
            plugin_manager=self._plugin_manager,
        )

        # Setup environment (async operation)
        asyncio.run(
            self._plugin_manager.hook.boardfarm_setup_env(
                config=self._boardfarm_config,
                cmdline_args=self.cmdline_args,
                plugin_manager=self._plugin_manager,
                device_manager=self._device_manager,
            ),
        )

        # NOTE: We intentionally skip boardfarm_post_setup_env hook here.
        # That hook starts the interactive shell, which is not needed for
        # automated Robot Framework test execution.

        self._is_deployed = True
        self._logger.info("Boardfarm devices deployed successfully")

    def _release_devices(self) -> None:
        """Release boardfarm devices after use."""
        if not self._is_deployed:
            self._logger.debug("Devices not deployed, skipping release")
            return

        deployment_status = (
            {"status": "success"}
            if self._deployment_data.get("status") == "success"
            else {
                "status": "failed",
                "exception": self._deployment_data.get("exception"),
            }
        )

        self._plugin_manager.hook.boardfarm_release_devices(
            config=self._boardfarm_config,
            cmdline_args=self.cmdline_args,
            plugin_manager=self._plugin_manager,
            deployment_status=deployment_status,
            device_manager=self._device_manager,
        )

        self._is_deployed = False
        self._logger.info("Boardfarm devices released successfully")

    def _parse_env_req_tags(self, tags: list[str]) -> dict[str, Any] | None:
        """Parse env_req from test tags.

        Supports two formats:
        1. env_req:json_string - Inline JSON requirement
        2. env_req:preset_name - Predefined requirement name

        Args:
            tags: List of test tags

        Returns:
            Parsed environment requirement or None if not found.
        """
        for tag in tags:
            if tag.startswith("env_req:"):
                env_req_str = tag[8:]  # Remove "env_req:" prefix

                # Try parsing as JSON
                try:
                    return json.loads(env_req_str)
                except json.JSONDecodeError:
                    # Treat as preset name
                    return self._get_env_req_preset(env_req_str)

        return None

    def _get_env_req_preset(self, preset_name: str) -> dict[str, Any]:
        """Get predefined environment requirement by name.

        Args:
            preset_name: Name of the preset (e.g., "dual_stack", "ipv4_only")

        Returns:
            Environment requirement dictionary.
        """
        presets: dict[str, dict[str, Any]] = {
            "dual_stack": {
                "environment_def": {
                    "board": {"eRouter_Provisioning_mode": ["dual"]},
                },
            },
            "ipv4_only": {
                "environment_def": {
                    "board": {"eRouter_Provisioning_mode": ["ipv4"]},
                },
            },
            "ipv6_only": {
                "environment_def": {
                    "board": {"eRouter_Provisioning_mode": ["ipv6"]},
                },
            },
        }
        return presets.get(preset_name, {})

    def _validate_env_requirement(self, env_req: dict[str, Any]) -> None:
        """Validate that environment meets the requirement.

        Args:
            env_req: Environment requirement dictionary

        Raises:
            EnvironmentMismatchError: If environment doesn't match.
        """
        if self._boardfarm_config is None:
            return

        if not is_env_matching(env_req, self._boardfarm_config.env_config):
            msg = f"Environment mismatch. Required: {env_req}"
            raise EnvironmentMismatchError(msg)

    def _run_contingency_check(self, env_req: dict[str, Any]) -> None:
        """Run contingency check for the environment requirement.

        Args:
            env_req: Environment requirement dictionary
        """
        if self._device_manager is None:
            return

        self._plugin_manager.hook.contingency_check(
            env_req=env_req,
            device_manager=self._device_manager,
        )
