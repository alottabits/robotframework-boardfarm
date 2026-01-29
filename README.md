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
It adapts Boardfarm's plugin/runner lifecycle into Robot Framework test execution and exposes convenient keywords for tests.

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
- [Command Line Options](#command-line-options)
- [Keywords Provided](#keywords-provided)
- [Environment Requirements](#environment-requirements)
- [Running Tests - Examples](#running-tests---examples)
- [Development](#development)
- [License](#license)

---

## Overview

`robotframework-boardfarm` provides:

- **BoardfarmListener**: Manages device lifecycle (deployment at suite start, release at suite end)
- **BoardfarmLibrary**: Keywords for device access, configuration, and utilities
- **UseCaseLibrary**: High-level test operation keywords from `boardfarm3.use_cases` (RECOMMENDED)
- **DeviceMethodLibrary**: Low-level device method keywords (for advanced use cases)
- **Environment Validation**: Tag-based environment requirement filtering
- **Integration**: Seamless integration with Boardfarm's pluggy hook system

### Key Design Principle

Keywords in Robot Framework are implemented as **thin wrappers around Boardfarm use_cases**, ensuring:
- **Single source of truth**: Test logic lives in Boardfarm, not the integration layer
- **Portability**: Same use cases work for pytest-bdd and Robot Framework
- **Maintainability**: Changes in Boardfarm automatically available to all frameworks

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
│   "Acs Get Parameter Value    ${acs}    ${cpe}    param"        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 2: UseCaseLibrary (thin wrapper)                          │
│   Discovers boardfarm3.use_cases at runtime                     │
│   Zero business logic - just parameter passing                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)        │
│   get_parameter_value(acs, cpe, param) -> str                   │
│   SINGLE SOURCE OF TRUTH for test operations                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 4: Device Templates (boardfarm3/templates/*.py)           │
│   Low-level device operations (nbi.GPV, sw.get_uptime)          │
└─────────────────────────────────────────────────────────────────┘
```

### Lifecycle

```
Robot Framework Test Execution
         │
         ▼
┌────────────────────────────┐
│   BoardfarmListener        │  ← Lifecycle management
│   - start_suite()          │     (deploy/release devices)
│   - end_suite()            │
│   - start_test()           │  ← Environment validation
│   - end_test()             │
└────────────────────────────┘
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

All three tools now use the same command-line format:

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

## Keywords Architecture

All libraries use **dynamic discovery** to automatically adapt to Boardfarm API changes:

```
┌─────────────────────────────────────────────────────────────────┐
│ BoardfarmLibrary                                                │
│   Scope: Testbed infrastructure                                 │
│   Keywords: Get Device By Type, Get Boardfarm Config, etc.      │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ UseCaseLibrary (RECOMMENDED)                                    │
│   Scope: High-level test operations                             │
│   Source: boardfarm3.use_cases modules                          │
│   Keywords: Acs Get Parameter Value, Cpe Get Cpu Usage, etc.    │
│   Benefits: Single source of truth, portable, maintainable      │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ DeviceMethodLibrary (Advanced)                                  │
│   Scope: Low-level device methods                               │
│   Source: Device instances (nbi, gui, sw, hw)                   │
│   Keywords: Nbi GPV, Sw Get Seconds Uptime, etc.                │
│   Use when: No use_case exists for the operation                │
└─────────────────────────────────────────────────────────────────┘
```

**Why three libraries?**
- **BoardfarmLibrary**: Infrastructure keywords for device and config access
- **UseCaseLibrary**: High-level test operations (RECOMMENDED - matches pytest-bdd step definitions)
- **DeviceMethodLibrary**: Low-level device access (advanced use cases only)

---

## Keywords Provided

### BoardfarmLibrary - Testbed Infrastructure

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

### UseCaseLibrary - High-Level Test Operations (RECOMMENDED)

**Dynamically discovered from boardfarm3.use_cases modules:**

| Module | Example Keywords | Description |
|--------|------------------|-------------|
| `acs` | `Acs Get Parameter Value`, `Acs Set Parameter Value`, `Acs Initiate Reboot` | TR-069 operations via ACS |
| `cpe` | `Cpe Get Cpu Usage`, `Cpe Get Seconds Uptime`, `Cpe Factory Reset` | CPE device operations |
| `voice` | `Voice Call A Phone`, `Voice Answer A Call`, `Voice Disconnect The Call` | SIP/Voice operations |
| `networking` | `Networking Ping`, `Networking Dns Lookup`, `Networking Http Get` | Network testing |
| `wifi` | `Wifi Get Ssid`, `Wifi Connect Client To Wifi` | WiFi operations |
| `dhcp` | `Dhcp Release Lease`, `Dhcp Renew Lease` | DHCP operations |

**Keyword naming convention**: `<Module> <Function Name>`
- `acs.get_parameter_value()` → `Acs Get Parameter Value`
- `cpe.get_cpu_usage()` → `Cpe Get Cpu Usage`
- `voice.call_a_phone()` → `Voice Call A Phone`

### DeviceMethodLibrary - Low-Level Device Methods (Advanced)

Use when no use_case exists for the required operation.

| Device | Component | Example Keywords |
|--------|-----------|------------------|
| ACS | nbi | `Nbi GPV`, `Nbi SPV`, `Nbi Reboot` |
| ACS | gui | `Gui Login`, `Gui Logout` |
| CPE | sw | `Sw Get Seconds Uptime`, `Sw Reset` |
| CPE | hw | Hardware-specific methods |

**Generic fallback**:
| Keyword | Description |
|---------|-------------|
| `Call Device Method` | Call any method: `device_type`, `method.path`, `*args` |
| `Call Component Method` | Call component method: `device_type`, `component`, `method`, `*args` |

---

## Handling Evolving Boardfarm APIs

When Boardfarm adds new use_cases or methods, they are **automatically available** as keywords:

```robotframework
*** Settings ***
Library    BoardfarmLibrary
Library    UseCaseLibrary

*** Test Cases ***
Test Evolving APIs
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    
    # Use case keywords (auto-discovered from boardfarm3.use_cases)
    ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}    Device.DeviceInfo.SoftwareVersion
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    
    # Future use_cases automatically available when Boardfarm updates:
    # ${new_result}=    Acs New Operation    ${acs}    ${cpe}    args
```

---

## Deprecation Handling

Deprecation warnings are handled **by Boardfarm itself**. When Boardfarm methods are deprecated, they emit `DeprecationWarning` via Python's `warnings` module, which automatically appears in Robot Framework output:

```
WARN: DeprecationWarning: GetParameterValues is deprecated, use GPV instead
```

This ensures:
- Consistent warnings across all Boardfarm users (pytest, Robot Framework, direct API)
- Single source of truth for deprecation status
- No additional configuration needed in the integration

---

## Environment Requirements

Use tags to specify environment requirements:

```robotframework
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

### Skip Boot for Development

```bash
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --skip-boot \
        robot/tests/
```

### With Console Logs and Legacy Mode

```bash
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --legacy \
        --save-console-logs ./logs/ \
        --outputdir results \
        robot/tests/
```

### Example Test Suite (Recommended - UseCaseLibrary)

```robotframework
*** Settings ***
Library           BoardfarmLibrary
Library           UseCaseLibrary
Suite Setup       Log    Starting Boardfarm tests
Suite Teardown    Log    Completed Boardfarm tests

*** Test Cases ***
Test CPE Performance
    [Documentation]    Verify CPE performance using use_case keywords
    ${cpe}=    Get Device By Type    CPE
    
    # Use case keywords (same logic as pytest-bdd step definitions)
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
    
    Should Be True    ${cpu} < 90    CPU usage too high
    Log    CPU: ${cpu}%, Uptime: ${uptime}s

Test ACS Operations
    [Documentation]    Test TR-069 parameter operations
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    
    # Check CPE is online
    ${online}=    Acs Is Cpe Online    ${acs}    ${cpe}
    Should Be True    ${online}
    
    # Get firmware version
    ${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
    ...    Device.DeviceInfo.SoftwareVersion
    Log    Firmware: ${version}

Test Voice Call
    [Documentation]    Test basic voice call
    ${phone1}=    Get Device By Type    SIPPhone    index=0
    ${phone2}=    Get Device By Type    SIPPhone    index=1
    
    Voice Call A Phone    ${phone1}    ${phone2}
    Voice Answer A Call    ${phone2}
    ${connected}=    Voice Is Call Connected    ${phone1}
    Should Be True    ${connected}
    Voice Disconnect The Call    ${phone1}

Test With Environment Requirement
    [Documentation]    Test requiring dual stack
    [Tags]    env_req:dual_stack
    Log Step    Environment validated
    ${cpe}=    Get Device By Type    CPE
    Log    Test passed with CPE: ${cpe}
```

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
| **Test Operations** | Step definitions → use_cases | UseCaseLibrary → use_cases |
| **Environment Req** | `@pytest.mark.env_req` | `[Tags] env_req:...` |
| **Lifecycle** | pytest hooks | Listener API |
| **Reports** | pytest-html integration | Robot Framework reports |

### CLI Consistency

All three tools use the same command-line format for boardfarm options:

```bash
boardfarm --board-name X --env-config Y --inventory-config Z
pytest   --board-name X --env-config Y --inventory-config Z tests/
bfrobot  --board-name X --env-config Y --inventory-config Z robot/tests/
```

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

```robotframework
# Robot Framework keyword (calls the same use_case)
${version}=    Acs Get Parameter Value    ${acs}    ${cpe}
...    Device.DeviceInfo.SoftwareVersion
```

---

## License

The robotframework-boardfarm package follows the same licensing as Boardfarm (Clear BSD).
See the [LICENSE](LICENSE) file for details.
