"""Dynamic Robot Framework library exposing Boardfarm use_cases as keywords.

This module provides a dynamic library that automatically exposes functions
from `boardfarm3.use_cases` modules as Robot Framework keywords. This enables
the same use cases to be used by both pytest-bdd and Robot Framework, ensuring
a single source of truth for test operations.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Layer 1: Robot Framework Test (.robot)                          │
    │   "Acs Get Parameter Value    ${acs}    ${cpe}    param"        │
    └─────────────────────────────────┬───────────────────────────────┘
                                      │
    ┌─────────────────────────────────▼───────────────────────────────┐
    │ Layer 2: UseCaseLibrary (this module)                           │
    │   Thin wrapper: discovers and exposes use_cases as keywords     │
    │   Zero business logic - just parameter passing                  │
    └─────────────────────────────────┬───────────────────────────────┘
                                      │
    ┌─────────────────────────────────▼───────────────────────────────┐
    │ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)        │
    │   get_parameter_value(acs, cpe, param) -> str                   │
    │   HIGH-LEVEL TEST OPERATIONS - business logic lives here        │
    └─────────────────────────────────────────────────────────────────┘

Key Benefits:
    - **Single source of truth**: Test logic maintained in Boardfarm use_cases
    - **Portability**: Same use cases work for pytest-bdd and Robot Framework
    - **Maintainability**: Fix a bug in use_cases, both frameworks benefit
    - **Documentation**: Use cases document which test statements they implement
    - **Dynamic discovery**: New use cases automatically become keywords

Example:
    *** Settings ***
    Library    BoardfarmLibrary
    Library    UseCaseLibrary

    *** Test Cases ***
    Test CPE Performance
        ${cpe}=    Get Device By Type    CPE
        ${cpu}=    Acs Get Cpu Usage    ${cpe}
        ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
        Should Be True    ${cpu} < 90

    Test ACS Parameter Operations
        ${acs}=    Get Device By Type    ACS
        ${cpe}=    Get Device By Type    CPE
        ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
        ...    Device.DeviceInfo.SoftwareVersion
        Log    Firmware version: ${version}

    Test Voice Call
        ${phone1}=    Get Device By Type    SIPPhone    index=0
        ${phone2}=    Get Device By Type    SIPPhone    index=1
        Voice Call A Phone    ${phone1}    ${phone2}
        ${ringing}=    Voice Is Call Ringing    ${phone2}
        Should Be True    ${ringing}
        Voice Answer A Call    ${phone2}
        Voice Disconnect The Call    ${phone1}
"""

from __future__ import annotations

import importlib
import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable

from robot.api import logger

if TYPE_CHECKING:
    from types import ModuleType


class UseCaseLibrary:
    """Dynamic library that exposes Boardfarm use_cases as Robot Framework keywords.

    This library uses Robot Framework's dynamic library API to automatically
    expose functions from `boardfarm3.use_cases` modules as keywords. Functions
    are discovered at runtime through introspection.

    Keyword Naming Convention:
        Module function names are converted to Robot Framework keywords using
        the pattern: "<Module> <Function Name>"

        Examples:
            - acs.get_parameter_value() -> "Acs Get Parameter Value"
            - cpe.get_cpu_usage() -> "Cpe Get Cpu Usage"
            - voice.call_a_phone() -> "Voice Call A Phone"
            - networking.ping() -> "Networking Ping"

    Module Discovery:
        The library introspects the following use_cases modules:
        - acs: ACS/TR-069 operations (GPV, SPV, reboot, log monitoring)
        - cpe: CPE operations (CPU, memory, uptime, factory reset)
        - voice: SIP/Voice operations (call, answer, disconnect)
        - networking: Network operations (ping, HTTP, DNS)
        - wifi: WiFi operations (SSID, client connections)
        - dhcp: DHCP operations (release, renew)
        - iperf: Performance testing (iperf client/server)
        - And more...

    Arguments:
        modules: Optional list of module names to discover (default: all known modules)
        exclude_modules: Optional list of module names to exclude

    Example:
        | Library | UseCaseLibrary |
        | ${cpe}= | Get Device By Type | CPE |
        | ${cpu}= | Cpe Get Cpu Usage | ${cpe} |
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    # Use case modules to introspect (relative to boardfarm3.use_cases)
    USE_CASE_MODULES = [
        "acs",
        "cpe",
        "voice",
        "networking",
        "wifi",
        "dhcp",
        "iperf",
        "device_getters",
        "device_utilities",
        "multicast",
        "ripv2",
        "image_comparison",
    ]

    # Functions to exclude from keyword generation
    EXCLUDED_FUNCTIONS = {
        # Internal/private functions that start with _ are already excluded
        # Add any public functions that shouldn't be keywords here
    }

    def __init__(
        self,
        modules: list[str] | None = None,
        exclude_modules: list[str] | None = None,
    ) -> None:
        """Initialize the use case library.

        Args:
            modules: List of module names to include (default: all known modules)
            exclude_modules: List of module names to exclude
        """
        self._modules_to_load = modules or self.USE_CASE_MODULES
        self._exclude_modules = set(exclude_modules or [])
        self._keyword_map: dict[str, tuple[Callable, str, str]] = {}  # kw -> (func, module, fname)
        self._doc_cache: dict[str, str] = {}
        self._argspec_cache: dict[str, list[str]] = {}
        self._discovered = False
        self._logger = logging.getLogger("boardfarm.robotframework.usecase")

    def _discover_keywords(self) -> None:
        """Discover keywords from use_cases modules.

        This method imports each configured module and extracts public functions
        as keywords. The discovery happens lazily on first access.
        """
        if self._discovered:
            return

        for module_name in self._modules_to_load:
            if module_name in self._exclude_modules:
                continue

            full_module_path = f"boardfarm3.use_cases.{module_name}"
            try:
                module = importlib.import_module(full_module_path)
                self._discover_module_keywords(module, module_name)
            except ImportError as e:
                self._logger.debug("Could not import %s: %s", full_module_path, e)
            except Exception as e:  # noqa: BLE001
                self._logger.warning(
                    "Error discovering keywords from %s: %s", full_module_path, e
                )

        self._discovered = True
        self._logger.info(
            "Discovered %d keywords from use_cases modules", len(self._keyword_map)
        )

    def _discover_module_keywords(self, module: ModuleType, module_name: str) -> None:
        """Discover keywords from a single module.

        Args:
            module: The imported module object
            module_name: Name of the module (e.g., "acs", "cpe")
        """
        # Convert module name to keyword prefix (e.g., "acs" -> "Acs")
        prefix = module_name.replace("_", " ").title().replace(" ", "")

        for name in dir(module):
            # Skip private/internal functions
            if name.startswith("_"):
                continue

            # Skip excluded functions
            if name in self.EXCLUDED_FUNCTIONS:
                continue

            attr = getattr(module, name, None)

            # Only include callable functions defined in this module
            if not callable(attr):
                continue
            if isinstance(attr, type):
                continue  # Skip classes
            if hasattr(attr, "__module__") and attr.__module__ != module.__name__:
                continue  # Skip imported functions

            # Build keyword name: "Acs Get Parameter Value"
            function_name = name.replace("_", " ").title()
            keyword_name = f"{prefix} {function_name}"

            # Cache the mapping
            self._keyword_map[keyword_name.lower()] = (attr, module_name, name)

            # Cache documentation
            doc = inspect.getdoc(attr) or f"Use case: {module_name}.{name}"
            self._doc_cache[keyword_name.lower()] = doc

            # Cache argument specification
            self._cache_argspec(keyword_name.lower(), attr)

    def _cache_argspec(self, keyword_lower: str, func: Callable) -> None:
        """Cache argument specification for a function.

        Args:
            keyword_lower: Lowercase keyword name (for cache key)
            func: The function to introspect
        """
        try:
            sig = inspect.signature(func)
            args = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param.default is inspect.Parameter.empty:
                    args.append(param_name)
                elif param.default is None:
                    args.append(f"{param_name}=None")
                else:
                    args.append(f"{param_name}={param.default!r}")
            self._argspec_cache[keyword_lower] = args
        except (ValueError, TypeError):
            self._argspec_cache[keyword_lower] = ["*args", "**kwargs"]

    # =========================================================================
    # Robot Framework Dynamic Library API
    # =========================================================================

    def get_keyword_names(self) -> list[str]:
        """Return list of available keywords (Robot Framework dynamic API).

        Returns:
            List of keyword names discovered from use_cases modules.
        """
        self._discover_keywords()

        # Return properly formatted keyword names (not lowercase)
        keywords = []
        for kw_lower in self._keyword_map:
            # Convert "acs get parameter value" to "Acs Get Parameter Value"
            keywords.append(kw_lower.title())

        return sorted(keywords)

    def run_keyword(self, name: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Execute a keyword (Robot Framework dynamic API).

        Note: Deprecation warnings are handled by Boardfarm itself using
        the debtcollector library. When Boardfarm functions emit
        DeprecationWarning, they appear in Robot Framework output.

        Args:
            name: Keyword name
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Result from the use_case function.
        """
        if kwargs is None:
            kwargs = {}

        self._discover_keywords()

        name_lower = name.lower()
        if name_lower not in self._keyword_map:
            msg = f"Unknown keyword: {name}"
            raise ValueError(msg)

        func, module_name, func_name = self._keyword_map[name_lower]

        # Log the call for debugging
        logger.info(f"Calling use_case: {module_name}.{func_name}")

        return func(*args, **kwargs)

    def get_keyword_documentation(self, name: str) -> str:
        """Return keyword documentation (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            Documentation string from the use_case function docstring.
        """
        if name == "__intro__":
            return self.__doc__ or ""

        self._discover_keywords()

        name_lower = name.lower()
        if name_lower in self._doc_cache:
            doc = self._doc_cache[name_lower]

            # Add keyword info header
            if name_lower in self._keyword_map:
                _, module_name, func_name = self._keyword_map[name_lower]
                header = f"Use case: boardfarm3.use_cases.{module_name}.{func_name}\n\n"
                return header + doc

            return doc

        return f"Keyword: {name}"

    def get_keyword_arguments(self, name: str) -> list[str]:
        """Return keyword arguments (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            List of argument specifications.
        """
        self._discover_keywords()

        name_lower = name.lower()
        return self._argspec_cache.get(name_lower, ["*args", "**kwargs"])

    def get_keyword_types(self, name: str) -> dict[str, type] | None:
        """Return keyword argument types (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            Dictionary mapping argument names to types, or None.
        """
        self._discover_keywords()

        name_lower = name.lower()
        if name_lower not in self._keyword_map:
            return None

        func, _, _ = self._keyword_map[name_lower]

        try:
            hints = func.__annotations__
            # Filter out return type
            return {k: v for k, v in hints.items() if k != "return"}
        except AttributeError:
            return None

    def get_keyword_tags(self, name: str) -> list[str]:
        """Return keyword tags (Robot Framework dynamic API).

        Tags are derived from the module name for easy filtering.

        Args:
            name: Keyword name

        Returns:
            List of tags for the keyword.
        """
        self._discover_keywords()

        name_lower = name.lower()
        if name_lower not in self._keyword_map:
            return []

        _, module_name, _ = self._keyword_map[name_lower]
        return [f"use_case:{module_name}"]

    def get_keyword_source(self, name: str) -> str | None:
        """Return keyword source location (Robot Framework dynamic API).

        Args:
            name: Keyword name

        Returns:
            Source file path and line number, or None.
        """
        self._discover_keywords()

        name_lower = name.lower()
        if name_lower not in self._keyword_map:
            return None

        func, _, _ = self._keyword_map[name_lower]

        try:
            source_file = inspect.getfile(func)
            source_lines = inspect.getsourcelines(func)
            line_number = source_lines[1] if source_lines else 0
            return f"{source_file}:{line_number}"
        except (TypeError, OSError):
            return None
