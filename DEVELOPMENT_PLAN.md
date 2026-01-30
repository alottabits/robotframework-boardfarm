# Robot Framework Boardfarm Integration - Development Plan

**Project**: robotframework-boardfarm  
**Goal**: Integrate Boardfarm testbed with Robot Framework as test execution and reporting engine  
**Reference**: pytest-boardfarm (existing pytest integration)  
**Created**: January 17, 2025  
**Updated**: January 29, 2026

---

## Executive Summary

This plan outlines the development of `robotframework-boardfarm`, a library that integrates the Boardfarm testbed framework with Robot Framework. The integration provides:

1. **BoardfarmListener**: Lifecycle management for device deployment/release
2. **BoardfarmLibrary**: Infrastructure keywords for device/config access
3. **bfrobot CLI**: Consistent command-line interface

**Key Design Principle**: Test keyword libraries should be created in the test project (e.g., boardfarm-bdd/robot/libraries/) and delegate to `boardfarm3.use_cases`. This mirrors the pytest-bdd step_defs approach.

---

## Architecture

### Recommended Architecture (Test Project Keyword Libraries)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Robot Framework Test (.robot)                          │
│   Test cases with scenario-aligned keywords                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ Layer 2: Keyword Libraries (test_project/robot/libraries/)      │
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
│   Low-level device operations                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Robot Framework                               │
│    ┌─────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│    │  Test Suites    │  │   Listener   │  │   Keyword Libraries   │  │
│    │  (.robot files) │  │  (lifecycle) │  │  (test project libs)  │  │
│    └────────┬────────┘  └──────┬───────┘  └───────────┬───────────┘  │
└─────────────┼──────────────────┼──────────────────────┼──────────────┘
              │                  │                      │
              └─────────────┬────┴───────────┬──────────┘
                            │                │
┌───────────────────────────▼────────────────▼─────────────────────────┐
│                     robotframework-boardfarm                          │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    BoardfarmListener                             │ │
│  │  - start_suite()  → Deploy devices (root suite only)            │ │
│  │  - end_suite()    → Release devices (root suite only)           │ │
│  │  - start_test()   → Contingency check, env_req validation       │ │
│  │  - end_test()     → Cleanup, logging                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    BoardfarmLibrary                              │ │
│  │  Infrastructure keywords:                                        │ │
│  │    - Get Device Manager, Get Boardfarm Config                   │ │
│  │    - Get Device By Type, Get Devices By Type                    │ │
│  │    - Log Step, Set/Get Test Context                             │ │
│  │    - Require Environment                                        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    CLI (bfrobot command)                         │ │
│  │  Consistent command-line interface                               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                          Boardfarm Core                               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    use_cases module                              │ │
│  │  High-level test operations (single source of truth):           │ │
│  │    cpe.py:        get_cpu_usage(), factory_reset(), tcpdump()   │ │
│  │    networking.py: ping(), http_get(), dns_lookup(), nmap_scan() │ │
│  │    voice.py:      call_a_phone(), answer_a_call(), disconnect() │ │
│  │    wifi.py:       connect_client(), scan_networks()             │ │
│  │    acs.py:        get_parameter_value(), set_parameter_value()  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────────┐ │
│  │PluginManager │  │ DeviceManager │  │    BoardfarmConfig         │ │
│  │(pluggy hooks)│  │               │  │ (inventory + env config)   │ │
│  └──────────────┘  └───────┬───────┘  └────────────────────────────┘ │
│                            │                                          │
│           ┌────────────────┼────────────────┐                        │
│           ▼                ▼                ▼                        │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐                    │
│     │   ACS    │    │   CPE    │    │   LAN    │  ...               │
│     │  .nbi    │    │  .sw     │    │          │                    │
│     │  .gui    │    │  .hw     │    │          │                    │
│     └──────────┘    └──────────┘    └──────────┘                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Test Project Structure (boardfarm-bdd)

The recommended approach is to create keyword libraries in the test project:

```
boardfarm-bdd/
├── tests/                          # pytest-bdd tests
│   ├── features/
│   │   └── acs_operations.feature
│   └── step_defs/
│       └── acs_steps.py            # pytest-bdd step definitions
│
├── robot/                          # Robot Framework tests
│   ├── tests/
│   │   └── acs_operations.robot
│   └── libraries/
│       └── acs_keywords.py         # Robot Framework keywords
│
└── pyproject.toml
```

### Keyword Library Pattern

```python
# robot/libraries/acs_keywords.py
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

    @keyword("Get CPE load average")
    def get_load_avg(self, cpe):
        """Direct device access when no use_case exists."""
        return cpe.sw.get_load_avg()
```

### Benefits

1. **Mirrors pytest-bdd structure**: `step_defs/` ↔ `libraries/`
2. **Same use_cases**: Both frameworks call `boardfarm3.use_cases`
3. **Scenario-aligned**: Keywords match test scenario language
4. **Maintainable**: Changes in one place benefit both frameworks
5. **Full access**: Keyword libraries have direct access to device objects when needed

---

## robotframework-boardfarm Components

### BoardfarmLibrary Keywords

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

## CLI Interface

### bfrobot Command

```bash
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        --outputdir results \
        robot/tests/
```

### Consistent with Other Tools

```bash
# All three tools use the same format:
boardfarm --board-name X --env-config Y --inventory-config Z
pytest   --board-name X --env-config Y --inventory-config Z tests/
bfrobot  --board-name X --env-config Y --inventory-config Z robot/tests/
```

---

## Implementation Status

### Completed

- [x] Project structure with `pyproject.toml`
- [x] BoardfarmListener (lifecycle management)
- [x] BoardfarmLibrary (infrastructure keywords)
- [x] bfrobot CLI
- [x] Environment requirement support
- [x] Documentation

### Removed (v0.2.0)

- [x] **UseCaseLibrary** - Removed in favor of test project keyword libraries
- [x] **DeviceMethodLibrary** - Removed; keyword libraries have direct device access

**Rationale**: With the top-down approach, keyword libraries in test projects have full Python access to both `boardfarm3.use_cases` and device objects. Auto-generating libraries from use_cases or device methods adds complexity without benefit.

---

## Change Log

### Version 0.2.0 (January 29, 2026)

**Breaking Changes**: Simplified to minimal footprint

Removed:
- `UseCaseLibrary` - Keywords should be created in test project
- `DeviceMethodLibrary` - Keyword libraries have direct device access

Remaining components:
- `BoardfarmListener` - Lifecycle management
- `BoardfarmLibrary` - Infrastructure keywords (Get Device By Type, etc.)
- `bfrobot` CLI - Command-line interface

**Benefits**:
- Clean separation: robotframework-boardfarm provides infrastructure only
- Test projects own their keywords
- Mirrors pytest-bdd step_defs pattern
- Keyword libraries have full access to boardfarm3 when needed

### Version 0.1.0 (January 25, 2026)

- Initial implementation with UseCaseLibrary, DeviceMethodLibrary, etc.

---

**Document Version**: 3.0  
**Last Updated**: January 29, 2026
