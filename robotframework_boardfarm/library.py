"""Robot Framework keyword library for Boardfarm testbed management.

This module provides keywords for accessing Boardfarm's testbed infrastructure
(DeviceManager, BoardfarmConfig) using dynamic discovery where possible.

Example:
    *** Settings ***
    Library    BoardfarmLibrary

    *** Test Cases ***
    Test Device Access
        ${cpe}=    Get Device By Type    CPE
        Log    CPE device: ${cpe}
"""

from __future__ import annotations

import inspect
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

    Methods on these objects are dynamically discovered, so new methods
    added to Boardfarm will be automatically available.

    = Architecture =

    This library complements DeviceMethodLibrary:
    - BoardfarmLibrary: Testbed infrastructure (DeviceManager, Config)
    - DeviceMethodLibrary: Device instance methods (ACS, CPE, etc.)

    = Example =

    | *** Settings ***
    | Library    BoardfarmLibrary
    |
    | *** Test Cases ***
    | Test Device Access
    |     ${dm}=    Get Device Manager
    |     ${cpe}=    Get Device By Type    CPE
    |     ${mode}=    Config Get Prov Mode
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    # Components to introspect for dynamic keywords
    _INTROSPECT_COMPONENTS = {
        "device_manager": "Dm",  # DeviceManager methods -> "Dm <Method>"
        "boardfarm_config": "Config",  # BoardfarmConfig methods -> "Config <Method>"
    }

    # Methods to exclude from dynamic discovery (internal/private)
    _EXCLUDED_METHODS = {
        # Common Python object methods
        "items", "keys", "values", "get", "pop", "update", "copy", "clear",
        # Internal methods we don't want exposed
        "register_device", "unregister_device",
    }

    def __init__(self) -> None:
        """Initialize the Boardfarm library."""
        self._context: dict[str, Any] = {}
        self._device_type_cache: dict[str, type] = {}
        self._keyword_cache: dict[str, tuple[str, str, Any]] = {}  # keyword -> (component, method, obj)

    # =========================================================================
    # Dynamic Library Protocol
    # =========================================================================

    def get_keyword_names(self) -> list[str]:
        """Return list of available keywords (Robot Framework dynamic library API).

        Keywords are dynamically discovered from:
        - DeviceManager methods (prefixed with "Dm")
        - BoardfarmConfig methods (prefixed with "Config")
        - Plus utility keywords defined in this class
        """
        keywords = []

        # Add utility keywords (decorated with @keyword)
        for name in dir(self):
            method = getattr(self, name, None)
            if callable(method) and hasattr(method, "robot_name"):
                keywords.append(method.robot_name)

        # Add dynamic keywords from testbed components
        try:
            listener = get_listener()
            for attr_name, prefix in self._INTROSPECT_COMPONENTS.items():
                obj = getattr(listener, attr_name, None)
                if obj is not None:
                    keywords.extend(self._discover_keywords(obj, prefix))
        except Exception:
            # Listener not ready - return only utility keywords
            pass

        return keywords

    def _discover_keywords(self, obj: Any, prefix: str) -> list[str]:
        """Discover keywords from an object's public methods."""
        keywords = []
        for name in dir(obj):
            if name.startswith("_"):
                continue
            if name in self._EXCLUDED_METHODS:
                continue
            method = getattr(obj, name, None)
            if callable(method) and not isinstance(method, type):
                kw_name = f"{prefix} {self._method_to_keyword_name(name)}"
                keywords.append(kw_name)
                self._keyword_cache[kw_name.lower()] = (prefix.lower(), name, None)
        return keywords

    def _method_to_keyword_name(self, method_name: str) -> str:
        """Convert Python method name to Robot Framework keyword style.

        Examples:
            get_device_by_type -> Get Device By Type
            GPV -> GPV
            get_prov_mode -> Get Prov Mode
        """
        # Handle already uppercase names (like GPV, SPV)
        if method_name.isupper():
            return method_name

        # Convert snake_case to Title Case
        words = method_name.split("_")
        return " ".join(word.capitalize() for word in words)

    def run_keyword(self, name: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Execute a keyword (Robot Framework dynamic library API).

        Note: Deprecation warnings are handled by Boardfarm itself.
        When Boardfarm methods emit DeprecationWarning, they appear
        in Robot Framework output automatically.
        """
        if kwargs is None:
            kwargs = {}

        name_lower = name.lower()

        # Check if it's a utility keyword
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "robot_name"):
                if method.robot_name.lower() == name_lower:
                    return method(*args, **kwargs)

        # Check if it's a dynamic keyword
        if name_lower in self._keyword_cache:
            prefix, method_name, _ = self._keyword_cache[name_lower]
            return self._run_dynamic_keyword(prefix, method_name, args, kwargs)

        # Try to discover and run (in case cache is stale)
        listener = get_listener()
        for attr_name, prefix in self._INTROSPECT_COMPONENTS.items():
            if name_lower.startswith(prefix.lower() + " "):
                obj = getattr(listener, attr_name, None)
                if obj is not None:
                    method_part = name[len(prefix) + 1:]  # Remove prefix and space
                    method_name = self._keyword_to_method_name(method_part)
                    if hasattr(obj, method_name):
                        method = getattr(obj, method_name)
                        return method(*args, **kwargs)

        msg = f"Unknown keyword: {name}"
        raise BoardfarmLibraryError(msg)

    def _run_dynamic_keyword(
        self, prefix: str, method_name: str, args: list[Any], kwargs: dict[str, Any]
    ) -> Any:
        """Execute a dynamically discovered keyword."""
        listener = get_listener()

        # Map prefix to attribute
        prefix_to_attr = {v.lower(): k for k, v in self._INTROSPECT_COMPONENTS.items()}
        attr_name = prefix_to_attr.get(prefix)
        if not attr_name:
            msg = f"Unknown prefix: {prefix}"
            raise BoardfarmLibraryError(msg)

        obj = getattr(listener, attr_name, None)
        if obj is None:
            msg = f"Component not available: {attr_name}"
            raise BoardfarmLibraryError(msg)

        method = getattr(obj, method_name, None)
        if method is None:
            msg = f"Method not found: {method_name} on {attr_name}"
            raise BoardfarmLibraryError(msg)

        return method(*args, **kwargs)

    def _keyword_to_method_name(self, keyword_name: str) -> str:
        """Convert Robot Framework keyword to Python method name.

        Examples:
            Get Device By Type -> get_device_by_type
            GPV -> GPV
        """
        # Handle uppercase keywords (like GPV)
        if keyword_name.isupper():
            return keyword_name

        # Convert Title Case to snake_case
        return "_".join(word.lower() for word in keyword_name.split())

    def get_keyword_documentation(self, name: str) -> str:
        """Return keyword documentation (Robot Framework dynamic library API)."""
        name_lower = name.lower()

        # Check utility keywords
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "robot_name"):
                if method.robot_name.lower() == name_lower:
                    return inspect.getdoc(method) or ""

        # Check dynamic keywords
        if name_lower in self._keyword_cache:
            prefix, method_name, _ = self._keyword_cache[name_lower]
            return self._get_dynamic_documentation(prefix, method_name)

        return ""

    def _get_dynamic_documentation(self, prefix: str, method_name: str) -> str:
        """Get documentation for a dynamically discovered keyword."""
        try:
            listener = get_listener()
            prefix_to_attr = {v.lower(): k for k, v in self._INTROSPECT_COMPONENTS.items()}
            attr_name = prefix_to_attr.get(prefix)
            if attr_name:
                obj = getattr(listener, attr_name, None)
                if obj:
                    method = getattr(obj, method_name, None)
                    if method:
                        doc = inspect.getdoc(method) or ""
                        sig = self._get_method_signature(method)
                        return f"{doc}\n\nSignature: {method_name}{sig}"
        except Exception:
            pass
        return f"Dynamically discovered method: {prefix}.{method_name}"

    def _get_method_signature(self, method: Any) -> str:
        """Get method signature as string."""
        try:
            sig = inspect.signature(method)
            return str(sig)
        except (ValueError, TypeError):
            return "(...)"

    def get_keyword_arguments(self, name: str) -> list[str]:
        """Return keyword arguments (Robot Framework dynamic library API)."""
        name_lower = name.lower()

        # Check utility keywords
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "robot_name"):
                if method.robot_name.lower() == name_lower:
                    return self._extract_arguments(method)

        # Check dynamic keywords
        if name_lower in self._keyword_cache:
            prefix, method_name, _ = self._keyword_cache[name_lower]
            return self._get_dynamic_arguments(prefix, method_name)

        return []

    def _extract_arguments(self, method: Any) -> list[str]:
        """Extract argument names from a method."""
        try:
            sig = inspect.signature(method)
            args = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param.default is inspect.Parameter.empty:
                    args.append(param_name)
                else:
                    args.append(f"{param_name}={param.default!r}")
            return args
        except (ValueError, TypeError):
            return ["*args", "**kwargs"]

    def _get_dynamic_arguments(self, prefix: str, method_name: str) -> list[str]:
        """Get arguments for a dynamically discovered keyword."""
        try:
            listener = get_listener()
            prefix_to_attr = {v.lower(): k for k, v in self._INTROSPECT_COMPONENTS.items()}
            attr_name = prefix_to_attr.get(prefix)
            if attr_name:
                obj = getattr(listener, attr_name, None)
                if obj:
                    method = getattr(obj, method_name, None)
                    if method:
                        return self._extract_arguments(method)
        except Exception:
            pass
        return ["*args", "**kwargs"]

    # =========================================================================
    # Utility Keywords (Robot Framework specific, not from Boardfarm)
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
    def get_device_by_type(self, device_type: str) -> BoardfarmDevice:
        """Get a device by its type name.

        Arguments:
        - device_type: The device type name (e.g., "CPE", "ACS", "LAN", "WAN")

        Example:
        | ${cpe}=    Get Device By Type    CPE
        | ${acs}=    Get Device By Type    ACS
        """
        dm = self.get_device_manager()
        device_class = self._resolve_device_type(device_type)
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
