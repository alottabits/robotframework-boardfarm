# Robot Framework Boardfarm Examples

This directory contains example test suites demonstrating how to use `robotframework-boardfarm`.

## Prerequisites

1. Install robotframework-boardfarm:
   ```bash
   pip install -e /path/to/robotframework-boardfarm
   ```

2. Ensure Boardfarm is installed and configured.

3. Have valid configuration files:
   - Environment config (e.g., `boardfarm_env.json`)
   - Inventory config (e.g., `boardfarm_config.json`)

## Running the Examples

### Use Case Tests (RECOMMENDED)

The recommended approach uses `UseCaseLibrary` which provides high-level test operations:

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:board_name=prplos-docker-1:env_config=./bf_config/boardfarm_env.json:inventory_config=./bf_config/boardfarm_config.json" \
      examples/use_case_test.robot
```

### Voice Call Tests

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:board_name=prplos-docker-1:env_config=./bf_config/boardfarm_env.json:inventory_config=./bf_config/boardfarm_config.json" \
      examples/voice_call_test.robot
```

### Networking Tests

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:board_name=prplos-docker-1:env_config=./bf_config/boardfarm_env.json:inventory_config=./bf_config/boardfarm_config.json" \
      examples/networking_test.robot
```

### Skip Boot Mode (Development)

For faster iteration during development, skip device boot:

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:board_name=my-board:env_config=./env.json:inventory_config=./inv.json:skip_boot=true" \
      examples/use_case_test.robot
```

## Example Files

| File | Description | Approach |
|------|-------------|----------|
| `use_case_test.robot` | CPE and ACS use case keywords | **RECOMMENDED** |
| `voice_call_test.robot` | Voice/SIP call testing | **RECOMMENDED** |
| `networking_test.robot` | Network testing (ping, DNS, HTTP) | **RECOMMENDED** |
| `basic_test.robot` | Basic device and config access | Legacy |
| `device_methods_test.robot` | Low-level device methods | Advanced |
| `env_requirement_test.robot` | Environment requirement examples | Infrastructure |

## Test Structure

### Recommended Pattern (UseCaseLibrary)

```robotframework
*** Settings ***
Library    BoardfarmLibrary
Library    UseCaseLibrary

*** Test Cases ***
Test CPE Performance
    ${cpe}=    Get Device By Type    CPE
    
    # Use case keywords (same logic as pytest-bdd step definitions)
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
```

### Environment Requirements

Use tags for environment requirements:

```robotframework
*** Test Cases ***
Test Dual Stack
    [Tags]    env_req:dual_stack
    # Test only runs in dual stack environments
```

Or use the keyword:

```robotframework
*** Test Cases ***
Test With Requirement
    Require Environment    dual_stack
    # Test continues only if requirement is met
```

## Benefits of UseCaseLibrary

1. **Single source of truth**: Same use_cases used by pytest-bdd step definitions
2. **Portability**: Tests can be easily migrated between frameworks
3. **Maintainability**: Fix once in use_cases, benefit everywhere
4. **Documentation**: Use cases document which test statements they implement
5. **Dynamic discovery**: New use cases automatically become keywords
