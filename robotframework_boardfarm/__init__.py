"""Robot Framework integration for Boardfarm testbed.

This package provides integration for running Robot Framework tests with Boardfarm:

1. **BoardfarmListener**: Lifecycle management (device deployment/release)
2. **BoardfarmLibrary**: Infrastructure keywords (device access, configuration)
3. **bfrobot CLI**: Command-line interface for running tests

= Architecture =

The recommended approach is to create scenario-aligned keyword libraries in your
test project (e.g., boardfarm-bdd/robot/libraries/) that delegate to Boardfarm
use_cases. This mirrors the pytest-bdd step definitions approach:

    ┌─────────────────────────────────────────────────────────────┐
    │ Layer 1: Robot Framework Test (.robot)                      │
    │   Test cases with scenario-aligned keywords                 │
    └───────────────────────────┬─────────────────────────────────┘
                                │
    ┌───────────────────────────▼─────────────────────────────────┐
    │ Layer 2: Keyword Libraries (your_project/robot/libraries/)  │
    │   @keyword decorator maps to scenario steps                 │
    │   Delegates to boardfarm3.use_cases or direct device access │
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

= BoardfarmLibrary Keywords =

    Get Device By Type      - Get device instance by type (CPE, ACS, etc.)
    Get Devices By Type     - Get all devices of a type
    Get Device Manager      - Get DeviceManager instance
    Get Boardfarm Config    - Get BoardfarmConfig instance
    Log Step                - Log a test step message
    Set/Get Test Context    - Store/retrieve values during test
    Require Environment     - Assert environment meets requirement

= Example Usage =

Using bfrobot CLI (recommended):

    bfrobot --board-name my-board \\
            --env-config ./env.json \\
            --inventory-config ./inv.json \\
            robot/tests/

Test file example:

    *** Settings ***
    Library    robotframework_boardfarm.BoardfarmLibrary
    Library    ../libraries/acs_keywords.py

    *** Test Cases ***
    Test CPE Online
        ${acs}=    Get Device By Type    ACS
        ${cpe}=    Get Device By Type    CPE
        The CPE Is Online Via ACS    ${acs}    ${cpe}
"""

__version__ = "0.2.0"
__pypi_url__ = "https://github.com/lgirdk/robotframework-boardfarm"

from robotframework_boardfarm.listener import BoardfarmListener
from robotframework_boardfarm.library import BoardfarmLibrary
from robotframework_boardfarm.exceptions import BoardfarmRobotError

__all__ = [
    "BoardfarmListener",
    "BoardfarmLibrary",
    "BoardfarmRobotError",
    "__version__",
]
