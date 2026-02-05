# Robot Framework Boardfarm

<p align="center">
  <img alt="Robot Framework" src="https://img.shields.io/badge/Robot%20Framework-6.0+-blue">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.11+-blue">
  <a href="https://github.com/psf/black"><img alt="Code style: black"
       src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
  <a href="https://github.com/astral-sh/ruff"><img alt="Lint: ruff"
       src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
</p>
<hr>

`robotframework-boardfarm` is the extension that integrates Boardfarm with Robot Framework.
It adapts Boardfarm's plugin/runner lifecycle into Robot Framework test execution and provides
device access keywords for tests.

> **Prerequisites**
>
> - Boardfarm must be installed and available on the Python path (expects boardfarm3 APIs)
> - Python 3.11+ is recommended
> - Robot Framework 6.0+

---

## Table of Contents

- [Overview](#overview)
- [Quick Install](#quick-install)
- [How It Works](#how-it-works)
- [Command Line Interface](#command-line-interface)
- [BoardfarmLibrary Keywords](#boardfarmlibrary-keywords)
- [Writing Tests](#writing-tests)
- [Environment Requirements](#environment-requirements)
- [Running Tests - Examples](#running-tests---examples)
- [Development](#development)
- [License](#license)

---

## Overview

`robotframework-boardfarm` provides:

- **BoardfarmListener**: Thin interface for testbed lifecycle (deployment at suite start, release at suite end)
- **BoardfarmLibrary**: Keywords for device access and utilities
- **bfrobot CLI**: Command-line tool for running tests with consistent Boardfarm options
- **Integration**: Seamless integration with Boardfarm's pluggy hook system

### Key Design Principles

1. **BoardfarmListener is a thin lifecycle interface** - It only handles device deployment and release, not test filtering or selection
2. **Device objects are the single source of truth** - All testbed data (IP addresses, phone numbers, credentials, network configuration) comes from device object properties, never from hard-coded variables
3. **Tests check their own preconditions** - Tests verify required devices are available and skip themselves if requirements aren't met
4. **Libraries are thin wrappers** - Keyword libraries delegate to `boardfarm3.use_cases`
5. **No hard-coded testbed configuration** - Resource files contain only true constants (timeouts, TR-069 paths), not testbed-specific values

Create keyword libraries in your test project (e.g., `robot/libraries/`):
- Use the `@keyword` decorator to map clean Python functions to scenario step text
- Extract all device data from device objects (e.g., `phone.number`, `sipcenter.ipv4_addr`)
- This mirrors the pytest-bdd step_defs approach for consistency
- Tests should NOT define local keywords - call library keywords directly

---

## Quick Install

```bash
pip install robotframework-boardfarm
```

### Development Install

```bash
git clone https://github.com/lgirdk/robotframework-boardfarm
cd robotframework-boardfarm
pip install -e ".[dev,test]"
```

---

## How It Works

### Architecture (Four-Layer Abstraction)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Robot Framework Test (.robot)                          │
│   Test cases with scenario-aligned keywords                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 2: Keyword Libraries (your_project/robot/libraries/)      │
│   @keyword decorator maps to scenario steps                     │
│   Delegates to boardfarm3.use_cases or direct device access     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)        │
│   SINGLE SOURCE OF TRUTH for test operations                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 4: Device Templates (boardfarm3/templates/*.py)           │
│   Low-level device operations (nbi.GPV, sw.get_uptime)          │
└─────────────────────────────────────────────────────────────────┘
```

### Lifecycle

The **BoardfarmListener** is a thin interface between Robot Framework and Boardfarm's testbed:

1. **Suite Start**: BoardfarmListener deploys devices via Boardfarm hooks
2. **Test Execution**: Tests query available devices and check their own preconditions
3. **Suite End**: BoardfarmListener releases devices

**Important**: The listener does NOT make test selection decisions. Tests are responsible for:
- Querying available devices via `Get Device By Type` / `Get Devices By Type`
- Checking if required devices are available
- Skipping themselves with `Skip` / `Skip If` when requirements aren't met

This keeps the listener focused on one job (testbed lifecycle) while tests remain self-documenting about their requirements.

---

## Command Line Interface

### The `bfrobot` Command (Recommended)

The `bfrobot` command provides a consistent CLI experience, matching the format used by `boardfarm` and `pytest`:

```bash
# Run Robot Framework tests with boardfarm
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --outputdir results \
        robot/tests/

# With skip-boot flag
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --skip-boot \
        robot/tests/hello.robot

# With legacy mode and console logs
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --legacy \
        --save-console-logs ./logs/ \
        robot/tests/
```

### Consistent CLI Across Tools

All three tools use the same command-line format:

```bash
# Boardfarm interactive shell
boardfarm --board-name prplos-docker-1 \
          --env-config ./bf_config/boardfarm_env.json \
          --inventory-config ./bf_config/boardfarm_config.json

# pytest with boardfarm
pytest --board-name prplos-docker-1 \
       --env-config ./bf_config/boardfarm_env.json \
       --inventory-config ./bf_config/boardfarm_config.json \
       tests/

# Robot Framework with boardfarm
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        robot/tests/
```

### Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--board-name` | Name of the board to use | Yes |
| `--env-config` | Path to environment JSON config | Yes |
| `--inventory-config` | Path to inventory JSON config | Yes |
| `--skip-boot` | Skip device booting | No |
| `--skip-contingency-checks` | Skip contingency checks | No |
| `--save-console-logs` | Path to save console logs | No |
| `--legacy` | Enable legacy device access mode | No |
| `--ignore-devices` | Comma-separated devices to ignore | No |

All standard Robot Framework options (`--outputdir`, `--include`, `--exclude`, `--test`, etc.) are also supported.

### Alternative: Direct Listener Usage

For advanced use cases, you can also use the listener directly:

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=prplos-docker-1:\
env_config=./bf_config/boardfarm_env.json:\
inventory_config=./bf_config/boardfarm_config.json" \
    robot/tests/
```

---

## BoardfarmLibrary Keywords

| Keyword | Description |
|---------|-------------|
| `Get Device Manager` | Returns the DeviceManager instance |
| `Get Device By Type` | Gets device by type string (e.g., "CPE", "ACS") |
| `Get Devices By Type` | Gets all devices of a type (returns dict) |
| `Get Boardfarm Config` | Returns the BoardfarmConfig instance |
| `Log Step` | Logs a test step message |
| `Set Test Context` | Stores a value in test context |
| `Get Test Context` | Retrieves a value from test context |

---

## Device Data Principles

**All testbed-specific data comes from device objects**, not hard-coded variables or configuration files.

### Why This Matters

- **Portability**: Tests work on any testbed without modification
- **Single source of truth**: Device objects contain accurate, live configuration
- **No duplication**: Eliminates hard-coded values that become stale

### Examples

```robot
*** Test Cases ***
Test Voice Call
    # ✅ CORRECT: Get device properties from objects
    ${phones}=    Get Devices By Type    SIPPhone
    ${phone_count}=    Get Length    ${phones}
    Skip If    ${phone_count} < 2    Requires at least 2 SIP phones
    
    @{phone_list}=    Get Dictionary Values    ${phones}
    ${phone_a}=    Set Variable    ${phone_list}[0]
    ${phone_b}=    Set Variable    ${phone_list}[1]
    
    # Phone number comes FROM the device object
    ${phone_a_number}=    Evaluate    $phone_a.number
    Log    Phone A number: ${phone_a_number}
    
    # ❌ WRONG: Hard-coded phone numbers
    # ${phone_number}=    Set Variable    1000
```

### What Should NOT Be Hard-Coded

| Data | Where It Comes From |
|------|---------------------|
| Phone numbers | `phone.number` property |
| IP addresses | `device.ipv4_addr`, `device.ipv6_addr` |
| SIP domain | `sipcenter.domain` or `sipcenter.name` |
| Credentials | `device.username`, `device.password` |
| Network subnets | Device interface properties |

### What Can Be Constants

| Data | Reason |
|------|--------|
| Timeouts | Sensible defaults (can be overridden) |
| TR-069 parameter paths | Standard paths that don't change per testbed |
| Test tags | Organizational metadata |

---

## Writing Tests

### Test Structure: Check Preconditions First

Tests should verify that required devices are available before proceeding:

```robot
*** Test Cases ***
UC-12348: Voice Call Test
    [Documentation]    Requires 2 SIP phones
    [Tags]    voice    requires-2-phones
    
    # Step 1: Check device availability
    ${phones}=    Get Devices By Type    SIPPhone
    ${phone_count}=    Get Length    ${phones}
    Skip If    ${phone_count} < 2
    ...    Test requires 2 SIP phones, testbed has ${phone_count}
    
    # Step 2: Get devices and extract properties FROM objects
    @{phone_list}=    Get Dictionary Values    ${phones}
    ${caller}=    Set Variable    ${phone_list}[0]
    ${callee}=    Set Variable    ${phone_list}[1]
    
    # Step 3: Execute test using device properties
    ${caller_number}=    Evaluate    $caller.number
    Log    Caller number: ${caller_number}
    # ... rest of test
```

### Recommended Approach: Keyword Libraries

Create scenario-aligned keyword libraries in your test project that delegate to `boardfarm3.use_cases`. This mirrors the pytest-bdd step_defs approach:

**Python Keyword Library** (`robot/libraries/acs_keywords.py`):

```python
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases

class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS."""
        return acs_use_cases.is_cpe_online(acs, cpe)

    @keyword("The ACS initiates a remote reboot of the CPE")
    def initiate_reboot(self, acs, cpe):
        """Initiate CPE reboot via ACS."""
        acs_use_cases.initiate_reboot(acs, cpe)
```

**Robot Test** (`robot/tests/reboot.robot`):

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/acs_keywords.py

*** Test Cases ***
UC-12347: Remote CPE Reboot
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}
    The ACS Initiates A Remote Reboot Of The CPE    ${acs}    ${cpe}
```

### Low-Level Device Access

Since keyword libraries are Python code, you have full access to device objects when needed:

```python
@keyword("Get CPE load average")
def get_load_avg(self, cpe):
    """Direct device access when no use_case exists."""
    return cpe.sw.get_load_avg()
```

### Comparison with pytest-bdd

| pytest-bdd | Robot Framework |
|------------|-----------------|
| `@when("step text")` | `@keyword("step text")` |
| `tests/step_defs/acs_steps.py` | `robot/libraries/acs_keywords.py` |
| `boardfarm3.use_cases.acs` | `boardfarm3.use_cases.acs` (same) |

Both frameworks use the same `boardfarm3.use_cases` as the single source of truth.

---

## Running Tests - Examples

### Basic Execution

```bash
# Using bfrobot (recommended - consistent with pytest and boardfarm)
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --outputdir results \
        robot/tests/
```

### Run Specific Tests

```bash
# Run a single test file
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        robot/tests/hello.robot

# Run tests by tag
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --include smoke \
        robot/tests/

# Run tests by name pattern
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --test "*Reboot*" \
        robot/tests/
```

### Example Test Suite

```robot
*** Settings ***
Library           robotframework_boardfarm.BoardfarmLibrary
Library           ../libraries/acs_keywords.py
Library           ../libraries/cpe_keywords.py
Suite Setup       Log    Starting Boardfarm tests
Suite Teardown    Log    Completed Boardfarm tests

*** Test Cases ***
Test CPE Online
    [Documentation]    Verify CPE is online via ACS
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}

Test CPE Reboot
    [Documentation]    Test remote CPE reboot
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The Operator Initiates A Reboot Task On The ACS For The CPE    ${acs}    ${cpe}
    The CPE Should Have Rebooted    ${cpe}

Test With Environment Requirement
    [Documentation]    Test requiring dual stack
    [Tags]    env_req:dual_stack
    Log Step    Environment validated
    ${cpe}=    Get Device By Type    CPE
    Log    Test passed with CPE: ${cpe}
```

---

## Deprecation Handling

Deprecation warnings are handled **by Boardfarm itself**. When Boardfarm methods are deprecated, they emit `DeprecationWarning` via Python's `warnings` module, which automatically appears in Robot Framework output.

---

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/lgirdk/robotframework-boardfarm
cd robotframework-boardfarm

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev,test]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=robotframework_boardfarm --cov-report=html
```

### Code Quality

```bash
# Run linter
ruff check .

# Run type checker
mypy robotframework_boardfarm

# Format code
ruff format .
```

---

## Comparison with pytest-boardfarm

| Feature | pytest-boardfarm | robotframework-boardfarm |
|---------|-----------------|-------------------------|
| **CLI Command** | `pytest --board-name ...` | `bfrobot --board-name ...` |
| **Entry Point** | pytest plugin | Robot Framework listener |
| **Device Access** | Fixtures | Keywords |
| **Test Operations** | Step definitions → use_cases | Keyword libraries → use_cases |
| **Environment Req** | `@pytest.mark.env_req` | `[Tags] env_req:...` |
| **Lifecycle** | pytest hooks | Listener API |
| **Reports** | pytest-html integration | Robot Framework reports |

### Framework Portability

Both frameworks use the same `boardfarm3.use_cases` as the single source of truth:

```python
# pytest-bdd step definition
@when("the operator gets the firmware version")
def get_firmware(acs, cpe, bf_context):
    version = acs_use_cases.get_parameter_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )
    bf_context.firmware_version = version
```

```python
# Robot Framework keyword library
@keyword("The operator gets the firmware version")
def get_firmware(self, acs, cpe):
    return acs_use_cases.get_parameter_value(
        acs, cpe, "Device.DeviceInfo.SoftwareVersion"
    )
```

---

## License

The robotframework-boardfarm package follows the same licensing as Boardfarm (Clear BSD).
See the [LICENSE](LICENSE) file for details.
