"""Robot Framework keyword library for Boardfarm testbed management.

This module provides keywords for accessing Boardfarm's testbed infrastructure
(DeviceManager, BoardfarmConfig).

Example:
    *** Settings ***
    Library    BoardfarmLibrary

    *** Test Cases ***
    Test Device Access
        ${cpe}=    Get Device By Type    CPE
        Log    CPE device: ${cpe}
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from robot.api import logger
from robot.api.deco import keyword, library

from robotframework_boardfarm.exceptions import (
    BoardfarmLibraryError,
)

if TYPE_CHECKING:
    from boardfarm3.devices.base_devices import BoardfarmDevice
    from boardfarm3.lib.boardfarm_config import BoardfarmConfig
    from boardfarm3.lib.device_manager import DeviceManager


def get_listener() -> Any:
    """Get the active BoardfarmListener instance."""
    from robotframework_boardfarm.listener import get_listener as _get_listener

    return _get_listener()


@library(scope="GLOBAL", version="0.1.0", doc_format="ROBOT")
class BoardfarmLibrary:
    """Robot Framework library for Boardfarm testbed management.

    This library provides access to Boardfarm's testbed infrastructure:
    - DeviceManager: for accessing deployed devices
    - BoardfarmConfig: for accessing configuration

    Keyword libraries in the test project (Layer 2) use these keywords
    to obtain device instances, then delegate to boardfarm3.use_cases
    (Layer 3) for test operations.

    = Example =

    | *** Settings ***
    | Library    BoardfarmLibrary
    |
    | *** Test Cases ***
    | Test Device Access
    |     ${dm}=    Get Device Manager
    |     ${cpe}=    Get Device By Type    CPE
    |     ${config}=    Get Boardfarm Config
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self) -> None:
        """Initialize the Boardfarm library."""
        self._context: dict[str, Any] = {}
        self._device_type_cache: dict[str, type] = {}

    # =========================================================================
    # Keywords
    # =========================================================================

    @keyword("Get Device Manager")
    def get_device_manager(self) -> DeviceManager:
        """Return the Boardfarm device manager.

        Returns the DeviceManager instance that holds all registered devices.

        Example:
        | ${dm}=    Get Device Manager
        | Log    Device manager: ${dm}
        """
        return get_listener().device_manager

    @keyword("Get Device By Type")
    def get_device_by_type(self, device_type: str, index: int | str | None = None) -> BoardfarmDevice:
        """Get a device by its type name.

        Arguments:
        - device_type: The device type name (e.g., "CPE", "ACS", "LAN", "WAN", "SIPPhone")
        - index: Optional index when multiple devices of the same type exist (0-based)

        When index is specified, returns the device at that index from the list of
        devices of that type. When index is not specified, returns the first/only device.

        Example:
        | ${cpe}=    Get Device By Type    CPE
        | ${acs}=    Get Device By Type    ACS
        | ${phone1}=    Get Device By Type    SIPPhone    index=0
        | ${phone2}=    Get Device By Type    SIPPhone    index=1
        """
        dm = self.get_device_manager()
        device_class = self._resolve_device_type(device_type)

        if index is not None:
            index_int = int(index)
            devices = dm.get_devices_by_type(device_class)
            device_list = list(devices.values())
            if not device_list:
                msg = f"No devices found of type: {device_type}"
                raise BoardfarmLibraryError(msg)
            if index_int < 0 or index_int >= len(device_list):
                msg = f"Index {index_int} out of range for {device_type} (found {len(device_list)} devices)"
                raise BoardfarmLibraryError(msg)
            return device_list[index_int]

        return dm.get_device_by_type(device_class)

    @keyword("Get Devices By Type")
    def get_devices_by_type(self, device_type: str) -> dict[str, BoardfarmDevice]:
        """Get all devices of a specific type.

        Arguments:
        - device_type: The device type name (e.g., "LAN", "WLAN")

        Returns a dictionary of device_name: device pairs.

        Example:
        | ${lan_devices}=    Get Devices By Type    LAN
        """
        dm = self.get_device_manager()
        device_class = self._resolve_device_type(device_type)
        return dm.get_devices_by_type(device_class)

    @keyword("Get Boardfarm Config")
    def get_boardfarm_config(self) -> BoardfarmConfig:
        """Return the Boardfarm configuration.

        Returns the BoardfarmConfig instance with merged inventory
        and environment configuration.

        Example:
        | ${config}=    Get Boardfarm Config
        """
        return get_listener().boardfarm_config

    @keyword("Log Step")
    def log_step(self, message: str) -> None:
        """Log a test step message.

        Arguments:
        - message: The step message to log.

        Example:
        | Log Step    Connecting to DUT
        | Log Step    Verifying configuration
        """
        logger.info(f"[STEP] {message}", html=False)

    @keyword("Set Test Context")
    def set_test_context(self, key: str, value: Any) -> None:
        """Store a value in the test context.

        Arguments:
        - key: Context key
        - value: Value to store

        Example:
        | Set Test Context    original_config    ${config}
        """
        self._context[key] = value

    @keyword("Get Test Context")
    def get_test_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the test context.

        Arguments:
        - key: Context key
        - default: Default value if key not found

        Example:
        | ${config}=    Get Test Context    original_config
        | ${value}=    Get Test Context    missing_key    default_value
        """
        return self._context.get(key, default)

    @keyword("Clear Test Context")
    def clear_test_context(self) -> None:
        """Clear all values from the test context.

        Example:
        | Clear Test Context
        """
        self._context.clear()

    @keyword("Require Environment")
    def require_environment(self, requirement: str | dict[str, Any]) -> None:
        """Assert that the environment meets the requirement.

        If the environment doesn't meet the requirement, the test is skipped.

        Arguments:
        - requirement: Environment requirement as JSON string, dict, or preset name

        Example:
        | Require Environment    {"environment_def":{"board":{"eRouter_Provisioning_mode":["dual"]}}}
        | Require Environment    dual_stack
        """
        from robot.api import SkipExecution

        from robotframework_boardfarm.utils import is_env_matching

        if isinstance(requirement, str):
            try:
                req_dict = json.loads(requirement)
            except json.JSONDecodeError:
                req_dict = self._get_env_req_preset(requirement)
        else:
            req_dict = requirement

        config = self.get_boardfarm_config()
        if not is_env_matching(req_dict, config.env_config):
            msg = f"Environment requirement not met: {req_dict}"
            raise SkipExecution(msg)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _resolve_device_type(self, type_name: str) -> type:
        """Resolve device type class from string name."""
        if type_name in self._device_type_cache:
            return self._device_type_cache[type_name]

        type_mapping = {
            "CPE": "boardfarm3.templates.cpe.cpe.CPE",
            "ACS": "boardfarm3.templates.acs.acs.ACS",
            "LAN": "boardfarm3.templates.lan.LinuxLAN",
            "WAN": "boardfarm3.templates.wan.WAN",
            "WLAN": "boardfarm3.templates.wlan.WLAN",
            "PDU": "boardfarm3.templates.pdu.PDU",
            "TFTP": "boardfarm3.templates.tftp.TFTP",
            "SIPPHONE": "boardfarm3.templates.sip_phone.SIPPhone",
            "SIPSERVER": "boardfarm3.templates.sip_server.SIPServer",
        }

        if type_name.upper() in type_mapping:
            module_path = type_mapping[type_name.upper()]
            try:
                device_class = self._import_class(module_path)
                self._device_type_cache[type_name] = device_class
                return device_class
            except ImportError:
                pass

        try:
            module_path = f"boardfarm3.templates.{type_name.lower()}"
            module = __import__(module_path, fromlist=[type_name.upper()])
            device_class = getattr(module, type_name.upper())
            self._device_type_cache[type_name] = device_class
            return device_class
        except (ImportError, AttributeError):
            pass

        try:
            from boardfarm3.devices.base_devices import BoardfarmDevice

            self._device_type_cache[type_name] = BoardfarmDevice
            return BoardfarmDevice
        except ImportError as e:
            msg = f"Could not resolve device type: {type_name}"
            raise BoardfarmLibraryError(msg) from e

    @staticmethod
    def _import_class(full_path: str) -> type:
        """Import a class from its full module path."""
        module_path, class_name = full_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)

    def _get_env_req_preset(self, preset_name: str) -> dict[str, Any]:
        """Get predefined environment requirement by name."""
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
