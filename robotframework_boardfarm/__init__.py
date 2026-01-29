"""Robot Framework integration for Boardfarm testbed.

This package provides libraries for accessing Boardfarm, using dynamic
discovery to automatically adapt to Boardfarm API changes:

1. **BoardfarmLibrary**: Testbed infrastructure (DeviceManager, BoardfarmConfig)
2. **UseCaseLibrary**: High-level test operations from boardfarm3.use_cases (RECOMMENDED)
3. **DeviceMethodLibrary**: Low-level device methods (for advanced use cases)

= Architecture (Use Case-Based - Recommended) =

The recommended approach uses UseCaseLibrary which exposes Boardfarm use_cases
as keywords. This ensures the same test logic works for pytest-bdd and Robot
Framework with zero duplication:

    ┌─────────────────────────────────────────────────────────────┐
    │ Layer 1: Robot Framework Test (.robot)                      │
    │   "Acs Get Parameter Value    ${acs}    ${cpe}    param"    │
    └───────────────────────────┬─────────────────────────────────┘
                                │
    ┌───────────────────────────▼─────────────────────────────────┐
    │ Layer 2: UseCaseLibrary (thin wrapper)                      │
    │   Discovers use_cases at runtime, zero business logic       │
    └───────────────────────────┬─────────────────────────────────┘
                                │
    ┌───────────────────────────▼─────────────────────────────────┐
    │ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)    │
    │   Single source of truth for test operations                │
    └───────────────────────────┬─────────────────────────────────┘
                                │
    ┌───────────────────────────▼─────────────────────────────────┐
    │ Layer 4: Device Templates (boardfarm3/templates/*.py)       │
    │   Low-level device operations                               │
    └─────────────────────────────────────────────────────────────┘

= Libraries =

    ┌─────────────────────────────────────────────────────────────┐
    │ BoardfarmLibrary                                            │
    │   Scope: Testbed infrastructure                             │
    │   Keywords: Get Device By Type, Get Boardfarm Config, etc.  │
    └─────────────────────────────────────────────────────────────┘
    ┌─────────────────────────────────────────────────────────────┐
    │ UseCaseLibrary (RECOMMENDED)                                │
    │   Scope: High-level test operations                         │
    │   Source: boardfarm3.use_cases modules                      │
    │   Keywords: Acs Get Parameter Value, Cpe Get Cpu Usage, etc.│
    │   Benefits: Single source of truth, portable, maintainable  │
    └─────────────────────────────────────────────────────────────┘
    ┌─────────────────────────────────────────────────────────────┐
    │ DeviceMethodLibrary (Advanced)                              │
    │   Scope: Low-level device methods                           │
    │   Source: Device instances (nbi, gui, sw, hw)               │
    │   Keywords: Nbi GPV, Sw Get Seconds Uptime, etc.            │
    │   Use when: No use_case exists for the operation            │
    └─────────────────────────────────────────────────────────────┘

= Example Usage (Recommended) =

    robot --listener robotframework_boardfarm.BoardfarmListener:board_name=my-board:env_config=./env.json:inventory_config=./inv.json tests/

    *** Settings ***
    Library    BoardfarmLibrary
    Library    UseCaseLibrary

    *** Test Cases ***
    Test CPE Performance
        ${cpe}=    Get Device By Type    CPE
        ${cpu}=    Cpe Get Cpu Usage    ${cpe}
        ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
        Should Be True    ${cpu} < 90
        Log    CPU: ${cpu}%, Uptime: ${uptime}s

    Test ACS Operations
        ${acs}=    Get Device By Type    ACS
        ${cpe}=    Get Device By Type    CPE
        ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
        ...    Device.DeviceInfo.SoftwareVersion
        Log    Firmware: ${version}

    Test Voice Call
        ${phone1}=    Get Device By Type    SIPPhone    index=0
        ${phone2}=    Get Device By Type    SIPPhone    index=1
        Voice Call A Phone    ${phone1}    ${phone2}
        Voice Answer A Call    ${phone2}
        Voice Disconnect The Call    ${phone1}
"""

__version__ = "0.1.0"
__pypi_url__ = "https://github.com/lgirdk/robotframework-boardfarm"

from robotframework_boardfarm.listener import BoardfarmListener
from robotframework_boardfarm.library import BoardfarmLibrary
from robotframework_boardfarm.use_case_library import UseCaseLibrary
from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary
from robotframework_boardfarm.exceptions import BoardfarmRobotError

__all__ = [
    "BoardfarmListener",
    "BoardfarmLibrary",
    "UseCaseLibrary",
    "DeviceMethodLibrary",
    "BoardfarmRobotError",
    "__version__",
]
