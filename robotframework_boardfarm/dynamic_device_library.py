"""Dynamic Robot Framework library for Boardfarm device method access.

This module provides a dynamic library that automatically exposes device methods
as Robot Framework keywords. It uses introspection to discover available methods
on devices, making the library automatically adapt to Boardfarm API changes.

Key Features:
- Automatic keyword generation from device methods
- Runtime introspection of device interfaces
- Support for nested components (acs.nbi, cpe.sw, cpe.hw)
- Automatic documentation generation from docstrings
- Deprecation warnings for deprecated methods
- Type conversion for Robot Framework compatibility

Usage:
    *** Settings ***
    Library    DeviceMethodLibrary    device_type=ACS

    *** Test Cases ***
    Test GPV
        ${result}=    Nbi GPV    Device.DeviceInfo.    cpe_id=${CPE_ID}
        Log    ${result}
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable

from robot.api import logger

if TYPE_CHECKING:
    from boardfarm3.devices.base_devices import BoardfarmDevice


class DeviceMethodLibrary:
    """Dynamic library that exposes device methods as Robot Framework keywords.

    This library uses Robot Framework's dynamic library API to automatically
    expose methods from Boardfarm devices as keywords. Methods are discovered
    at runtime through introspection.

    The library supports two modes:
    1. Device-specific: Library bound to a specific device type
    2. Generic: Library can call methods on any device

    Arguments:
        device_type: Optional device type to bind to (e.g., "ACS", "CPE")
        device_name: Optional specific device name to bind to

    Example (Device-specific):
        | Library | DeviceMethodLibrary | device_type=ACS |
        | ${result}= | Nbi GPV | Device.DeviceInfo. |

    Example (Generic):
        | Library | DeviceMethodLibrary |
        | ${result}= | Call Device Method | ACS | nbi.GPV | Device.DeviceInfo. |
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    # Methods to exclude from keyword generation
    EXCLUDED_METHODS = {
        "__init__",
        "__repr__",
        "__str__",
        "__hash__",
        "__eq__",
        "__ne__",
        "_warn_deprecation",
    }

    # Prefixes for methods to exclude
    EXCLUDED_PREFIXES = ("_",)

    def __init__(
        self,
        device_type: str | None = None,
        device_name: str | None = None,
    ) -> None:
        """Initialize the dynamic device library.

        Args:
            device_type: Device type to bind to (e.g., "ACS", "CPE", "LAN")
            device_name: Specific device name to bind to
        """
        self._device_type = device_type
        self._device_name = device_name
        self._keyword_cache: dict[str, Callable] = {}
        self._doc_cache: dict[str, str] = {}
        self._argspec_cache: dict[str, list[str]] = {}
        self._device_cache: BoardfarmDevice | None = None
        self._logger = logging.getLogger("boardfarm.robotframework.dynamic")

    def _get_device(self) -> BoardfarmDevice:
        """Get the device instance (cached)."""
        if self._device_cache is not None:
            return self._device_cache

        from robotframework_boardfarm.listener import get_listener

        listener = get_listener()
        dm = listener.device_manager

        if self._device_name:
            # Get by specific name
            devices = {
                name: dev
                for name, dev in dm._plugin_manager.list_name_plugin()
                if name == self._device_name
            }
            if self._device_name not in devices:
                msg = f"Device '{self._device_name}' not found"
                raise ValueError(msg)
            self._device_cache = devices[self._device_name]
        elif self._device_type:
            # Get by type
            from robotframework_boardfarm.library import BoardfarmLibrary

            lib = BoardfarmLibrary()
            device_class = lib._resolve_device_type(self._device_type)
            self._device_cache = dm.get_device_by_type(device_class)
        else:
            msg = "Either device_type or device_name must be specified"
            raise ValueError(msg)

        return self._device_cache

    def get_keyword_names(self) -> list[str]:
        """Return list of available keywords (Robot Framework dynamic API).

        This method is called by Robot Framework to discover available keywords.
        Keywords are generated dynamically from device methods.

        Returns:
            List of keyword names.
        """
        # Always include the generic method
        keywords = ["Call Device Method", "Call Component Method"]

        # If device type specified, add device-specific keywords
        if self._device_type or self._device_name:
            try:
                device = self._get_device()
                keywords.extend(self._discover_device_keywords(device))
            except Exception as e:
                self._logger.warning(f"Could not discover device keywords: {e}")

        return keywords

    def _discover_device_keywords(
        self,
        device: BoardfarmDevice,
        prefix: str = "",
    ) -> list[str]:
        """Discover keywords from device methods.

        Args:
            device: Device instance to introspect
            prefix: Prefix for nested components (e.g., "Nbi" for acs.nbi)

        Returns:
            List of keyword names.
        """
        keywords = []

        for name in dir(device):
            if name in self.EXCLUDED_METHODS:
                continue
            if name.startswith(self.EXCLUDED_PREFIXES):
                continue

            try:
                attr = getattr(device, name)
            except (NotImplementedError, AttributeError):
                continue

            if callable(attr) and not isinstance(attr, type):
                keyword_name = self._method_to_keyword_name(name, prefix)
                keywords.append(keyword_name)
                self._cache_method_info(keyword_name, attr)

            elif hasattr(attr, "__class__") and not isinstance(
                attr, (str, int, float, bool, list, dict, type(None))
            ):
                # This is a component (like nbi, gui, sw, hw)
                # Discover its methods too
                component_prefix = (
                    f"{prefix} {name.title()}" if prefix else name.title()
                )
                component_keywords = self._discover_component_keywords(
                    attr, component_prefix
                )
                keywords.extend(component_keywords)

        return keywords

    def _discover_component_keywords(
        self,
        component: Any,
        prefix: str,
    ) -> list[str]:
        """Discover keywords from a device component (nbi, gui, sw, hw).

        Args:
            component: Component instance to introspect
            prefix: Prefix for keyword names (e.g., "Nbi", "Gui")

        Returns:
            List of keyword names.
        """
        keywords = []

        for name in dir(component):
            if name in self.EXCLUDED_METHODS:
                continue
            if name.startswith(self.EXCLUDED_PREFIXES):
                continue

            try:
                attr = getattr(component, name)
            except (NotImplementedError, AttributeError):
                continue

            if callable(attr) and not isinstance(attr, type):
                keyword_name = self._method_to_keyword_name(name, prefix)
                keywords.append(keyword_name)
                self._cache_method_info(keyword_name, attr)

        return keywords

    def _method_to_keyword_name(self, method_name: str, prefix: str = "") -> str:
        """Convert method name to Robot Framework keyword name.

        Args:
            method_name: Python method name (e.g., "GPV", "get_device_status")
            prefix: Optional prefix (e.g., "Nbi")

        Returns:
            Keyword name (e.g., "Nbi GPV", "Get Device Status")
        """
        # Convert snake_case to Title Case
        words = method_name.replace("_", " ").split()
        title_words = [w.title() if w.islower() else w for w in words]
        keyword = " ".join(title_words)

        if prefix:
            return f"{prefix} {keyword}"
        return keyword

    def _keyword_to_method_name(self, keyword_name: str) -> tuple[str, str]:
        """Convert keyword name back to method name and component.

        Args:
            keyword_name: Keyword name (e.g., "Nbi GPV")

        Returns:
            Tuple of (component_name, method_name) or ("", method_name)
        """
        parts = keyword_name.split()

        # Check if first part is a known component
        known_components = {"Nbi", "Gui", "Sw", "Hw", "Console", "Firewall"}

        if parts[0] in known_components:
            component = parts[0].lower()
            method_parts = parts[1:]
        else:
            component = ""
            method_parts = parts

        # Convert title case back to original method name
        # Handle special cases like "GPV", "SPV", "GPN" that should stay uppercase
        method_name = "_".join(p.lower() if p.lower() != p else p for p in method_parts)

        # Fix common abbreviations that should stay uppercase
        for abbrev in ["gpv", "spv", "gpn", "gpa", "spa", "rpc"]:
            method_name = method_name.replace(abbrev, abbrev.upper())

        return component, method_name

    def _cache_method_info(self, keyword_name: str, method: Callable) -> None:
        """Cache method information for keyword documentation.

        Args:
            keyword_name: Keyword name
            method: Method callable
        """
        self._keyword_cache[keyword_name] = method

        # Cache documentation
        doc = inspect.getdoc(method) or "No documentation available."
        self._doc_cache[keyword_name] = doc

        # Cache argument specification
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
            self._argspec_cache[keyword_name] = args
        except (ValueError, TypeError):
            self._argspec_cache[keyword_name] = ["*args", "**kwargs"]

    def run_keyword(self, name: str, args: list, kwargs: dict) -> Any:
        """Execute a keyword (Robot Framework dynamic API).

        Note: Deprecation warnings are handled by Boardfarm itself.
        When Boardfarm methods emit DeprecationWarning, they appear
        in Robot Framework output automatically.

        Args:
            name: Keyword name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Keyword result.
        """
        if name == "Call Device Method":
            return self._call_device_method(*args, **kwargs)
        elif name == "Call Component Method":
            return self._call_component_method(*args, **kwargs)
        else:
            return self._run_device_keyword(name, args, kwargs)

    def _run_device_keyword(self, name: str, args: list, kwargs: dict) -> Any:
        """Run a device-specific keyword.

        Args:
            name: Keyword name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Method result.
        """
        device = self._get_device()
        component, method_name = self._keyword_to_method_name(name)

        if component:
            # Get the component (e.g., device.nbi, device.gui)
            target = getattr(device, component)
        else:
            target = device

        method = getattr(target, method_name)
        logger.info(f"Calling {target.__class__.__name__}.{method_name}")

        return method(*args, **kwargs)

    def _call_device_method(
        self,
        device_type: str,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call a method on a device by type.

        This is a generic keyword that allows calling any method on any device
        without pre-binding the library to a specific device type.

        Args:
            device_type: Device type (e.g., "ACS", "CPE", "LAN")
            method_name: Method name (e.g., "nbi.GPV", "sw.get_seconds_uptime")
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            Method result.

        Example:
            | ${result}= | Call Device Method | ACS | nbi.GPV | Device.DeviceInfo. |
            | ${uptime}= | Call Device Method | CPE | sw.get_seconds_uptime |
        """
        from robotframework_boardfarm.listener import get_listener

        listener = get_listener()
        dm = listener.device_manager

        # Get device
        from robotframework_boardfarm.library import BoardfarmLibrary

        lib = BoardfarmLibrary()
        device_class = lib._resolve_device_type(device_type)
        device = dm.get_device_by_type(device_class)

        # Parse method path (e.g., "nbi.GPV" -> ["nbi", "GPV"])
        method_parts = method_name.split(".")
        target = device
        for part in method_parts[:-1]:
            target = getattr(target, part)

        method = getattr(target, method_parts[-1])
        logger.info(f"Calling {device_type}.{method_name}")

        return method(*args, **kwargs)

    def _call_component_method(
        self,
        device_type: str,
        component: str,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call a method on a device component.

        Similar to Call Device Method but with explicit component specification.

        Args:
            device_type: Device type (e.g., "ACS", "CPE")
            component: Component name (e.g., "nbi", "gui", "sw", "hw")
            method_name: Method name (e.g., "GPV", "get_seconds_uptime")
            *args: Method arguments
            **kwargs: Method keyword arguments

        Returns:
            Method result.

        Example:
            | ${result}= | Call Component Method | ACS | nbi | GPV | Device.DeviceInfo. |
            | ${uptime}= | Call Component Method | CPE | sw | get_seconds_uptime |
        """
        full_method = f"{component}.{method_name}"
        return self._call_device_method(device_type, full_method, *args, **kwargs)

    def get_keyword_documentation(self, name: str) -> str:
        """Return keyword documentation (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            Documentation string.
        """
        if name == "__intro__":
            return self.__doc__ or ""

        if name == "Call Device Method":
            return self._call_device_method.__doc__ or ""

        if name == "Call Component Method":
            return self._call_component_method.__doc__ or ""

        return self._doc_cache.get(name, "No documentation available.")

    def get_keyword_arguments(self, name: str) -> list[str]:
        """Return keyword arguments (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            List of argument specifications.
        """
        if name == "Call Device Method":
            return ["device_type", "method_name", "*args", "**kwargs"]

        if name == "Call Component Method":
            return ["device_type", "component", "method_name", "*args", "**kwargs"]

        return self._argspec_cache.get(name, ["*args", "**kwargs"])
