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

- **BoardfarmListener**: Manages device lifecycle (deployment at suite start, release at suite end)
- **BoardfarmLibrary**: Keywords for device access, configuration, and utilities
- **bfrobot CLI**: Command-line tool for running tests with consistent Boardfarm options
- **Environment Validation**: Tag-based environment requirement filtering
- **Integration**: Seamless integration with Boardfarm's pluggy hook system

### Key Design Principles

1. **Libraries are the single source of truth** - All keywords defined in Python libraries
2. **Tests contain no keyword definitions** - Test files call library keywords directly
3. **Libraries are thin wrappers** - Delegate to `boardfarm3.use_cases`

Create keyword libraries in your test project (e.g., `robot/libraries/`):
- Use the `@keyword` decorator to map clean Python functions to scenario step text
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

1. **Suite Start**: BoardfarmListener deploys devices via Boardfarm hooks
2. **Test Start**: Environment requirements are validated, contingency checks run
3. **Test Execution**: Keywords access devices and configuration
4. **Test End**: Cleanup and logging
5. **Suite End**: Devices are released

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
| `Get Devices By Type` | Gets all devices of a type |
| `Get Boardfarm Config` | Returns the BoardfarmConfig instance |
| `Log Step` | Logs a test step message |
| `Set Test Context` | Stores a value in test context |
| `Get Test Context` | Retrieves a value from test context |
| `Require Environment` | Asserts environment meets requirement |

---

## Writing Tests

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

## Environment Requirements

Use tags to specify environment requirements:

```robot
*** Test Cases ***
Test Dual Stack Mode
    [Tags]    env_req:dual_stack
    # Test runs only if environment supports dual stack

Test With JSON Requirement
    [Tags]    env_req:{"environment_def":{"board":{"eRouter_Provisioning_mode":["dual"]}}}
    # Test runs only if JSON requirement is met
```

### Preset Names

| Preset | Description |
|--------|-------------|
| `dual_stack` | Requires dual stack provisioning mode |
| `ipv4_only` | Requires IPv4 only provisioning mode |
| `ipv6_only` | Requires IPv6 only provisioning mode |

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
