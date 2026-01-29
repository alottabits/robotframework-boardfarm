# Robot Framework Boardfarm Integration - Development Plan

**Project**: robotframework-boardfarm  
**Goal**: Integrate Boardfarm testbed with Robot Framework as test execution and reporting engine  
**Reference**: pytest-boardfarm (existing pytest integration)  
**Created**: January 17, 2025  
**Updated**: January 25, 2026

---

## Executive Summary

This plan outlines the development of `robotframework-boardfarm`, a library that integrates the Boardfarm testbed framework with Robot Framework. The integration leverages **Boardfarm's use_cases module** as the primary abstraction layer, providing a clean separation between test framework concerns (Robot Framework) and testbed operations (Boardfarm).

**Key Design Principle**: Keywords in Robot Framework are implemented as thin wrappers around Boardfarm use cases, which in turn leverage device methods. This ensures:
- **Single source of truth**: Test logic lives in Boardfarm, not the integration layer
- **Portability**: Same use cases work for pytest-boardfarm and robotframework-boardfarm
- **Maintainability**: Changes in Boardfarm automatically available to all test frameworks

---

## Analysis Summary

### Existing pytest-boardfarm Integration Pattern

The pytest-boardfarm integration provides:

1. **Plugin Registration** via pytest entry points (`pytest11`)
2. **Command Line Arguments** forwarded to Boardfarm's pluggy hooks
3. **Fixtures** for device access (`device_manager`, `boardfarm_config`, `bf_context`, `bf_logger`)
4. **Lifecycle Management** via pytest hooks:
   - `pytest_sessionstart` → Device reservation and config parsing
   - `pytest_runtestloop` → Device deployment and teardown
   - `pytest_runtest_setup` → Environment requirement validation
5. **HTML Report Integration** via pytest-html hooks
6. **Markers** for environment requirements (`@pytest.mark.env_req`)

### Boardfarm Core Architecture

Boardfarm uses:
- **Pluggy** for hook-based plugin system
- **DeviceManager** for device lifecycle management
- **BoardfarmConfig** for merged inventory/environment configuration
- **Async deployment** via `asyncio.run()` for environment setup

### Robot Framework Extension Points

Robot Framework provides several extension mechanisms:
1. **Listener Interface** - For test lifecycle hooks (similar to pytest hooks)
2. **Library API** - For creating keyword libraries
3. **Visitor API** - For modifying test data
4. **Pre-run Modifiers** - For filtering/modifying tests before execution
5. **Result Visitors** - For processing execution results

---

## Architecture Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Robot Framework                               │
│    ┌─────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│    │  Test Suites    │  │   Listener   │  │   Keyword Libraries   │  │
│    │  (.robot files) │  │  (lifecycle) │  │   (use case wrappers) │  │
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
│  │                  UseCaseLibrary (Dynamic)                        │ │
│  │  Introspects: boardfarm3.use_cases modules                      │ │
│  │  Keywords discovered at runtime from use_cases:                  │ │
│  │    - Cpe Get Cpu Usage, Cpe Factory Reset, Cpe Get Uptime       │ │
│  │    - Voice Call A Phone, Voice Answer A Call, Voice Disconnect  │ │
│  │    - Networking Ping, Networking Http Get, Networking Dns Lookup│ │
│  │    - Wifi Connect Client, Dhcp Release Lease, etc.              │ │
│  │  Maps 1:1 to Boardfarm use_cases functions                      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    Configuration & CLI                           │ │
│  │  - Listener arguments (board_name, config paths)                │ │
│  │  - Variable file support                                        │ │
│  │  - Environment requirement presets                              │ │
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
│  │    dhcp.py:       release_lease(), renew_lease()                │ │
│  │    iperf.py:      run_iperf_client(), run_iperf_server()        │ │
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

### Data Flow

```
Test Execution:
                                                                
  robot --listener BoardfarmListener:board_name=X tests/        
                        │                                        
                        ▼                                        
              ┌─────────────────┐                               
              │ BoardfarmListener│                               
              │   start_suite() │──────► Deploy devices          
              └────────┬────────┘                               
                       │                                        
                       ▼                                        
              ┌─────────────────┐                               
              │ BoardfarmLibrary│  Infrastructure keywords       
              │                 │  (device access, config, etc.) 
              └────────┬────────┘                               
                       │                                        
                       ▼                                        
            ┌───────────────────┐     ┌──────────────────────┐  
            │  UseCaseLibrary   │◄────│ Introspect at runtime│  
            │  (dynamic)        │     │ boardfarm3.use_cases │  
            └─────────┬─────────┘     │ modules              │  
                      │               └──────────────────────┘  
                      ▼                                         
            ┌───────────────────┐                               
            │ Boardfarm use_cases│  Single source of truth      
            │ (cpe, voice, etc.) │  for test operations          
            └─────────┬─────────┘                               
                      │                                         
                      ▼                                         
            ┌───────────────────┐                               
            │  Device Methods   │  Low-level device operations   
            │ (nbi, sw, console)│  (called by use_cases)         
            └───────────────────┘                               
```

### Abstraction Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: Robot Framework Test (.robot file)                         │
│   "Cpe Get Cpu Usage    ${board}"                                   │
│   "Voice Call A Phone   ${caller}    ${callee}"                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 2: UseCaseLibrary (robotframework-boardfarm)                  │
│   Thin wrapper: discovers and exposes use_cases as keywords         │
│   Zero business logic - just parameter passing                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 3: Boardfarm use_cases (boardfarm3/use_cases/*.py)            │
│   get_cpu_usage(board: CPE) -> float                                │
│   call_a_phone(caller: VoiceClient, callee: VoiceClient)            │
│   HIGH-LEVEL TEST OPERATIONS - business logic lives here            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│ Layer 4: Device Methods (boardfarm3/templates/*.py)                 │
│   board.sw.get_load_avg()                                           │
│   caller.dial(callee.number)                                        │
│   LOW-LEVEL DEVICE OPERATIONS                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Use Case-Based Abstraction (Primary Design Principle)**
   - Keywords map to Boardfarm `use_cases` module, NOT device methods
   - `use_cases` provide the right abstraction level for test operations
   - Examples: `get_cpu_usage()`, `call_a_phone()`, `ping()`, `factory_reset()`
   - Benefits:
     - **Single source of truth**: Test logic maintained in Boardfarm
     - **Portability**: Same use cases work for pytest and Robot Framework
     - **Maintainability**: No duplication of test logic
     - **Documentation**: Use cases already document which test statements they implement

2. **Listener-Based Lifecycle Management**
   - Use Robot Framework's Listener API (v3) for suite/test lifecycle
   - Deploy devices at suite start, release at suite end
   - Validate environment requirements at test start

3. **Dynamic Discovery Architecture**
   - **BoardfarmLibrary**: Infrastructure keywords (device access, config, context)
   - **UseCaseLibrary**: Introspects `boardfarm3.use_cases` modules at runtime
   - Automatically discovers new use cases when Boardfarm adds them
   - No code changes needed when use cases evolve

4. **Thin Integration Layer**
   - robotframework-boardfarm contains NO business logic
   - All test operations are implemented in Boardfarm use_cases
   - Integration layer only handles:
     - Robot Framework lifecycle hooks
     - Keyword discovery and parameter passing
     - Framework-specific utilities (logging, context)

5. **Configuration via Variables**
   - Board name, config paths via `--variable` or variable files
   - Support for `--listener` arguments
   - Compatible with existing Boardfarm config format

6. **Tag-Based Environment Requirements**
   - Use Robot Framework tags instead of pytest markers
   - `[Tags]  env_req:dual_stack` style tagging
   - Pre-run modifier for filtering incompatible tests

---

## Keyword Discovery Strategy

### Problem Statement

Test writers need keywords that match their test requirements:
- High-level operations like "Get CPU usage", "Ping a host", "Make a phone call"
- Not low-level device methods like `board.sw.get_load_avg()` or `caller.dial()`

Boardfarm already solves this with its `use_cases` module - we should leverage it!

### Solution: Use Case-Based Keywords

```
┌─────────────────────────────────────────────────────────────────────┐
│ BoardfarmLibrary                                                    │
│   Scope: Testbed infrastructure (static keywords)                   │
│   Keywords:                                                         │
│     - Get Device Manager, Get Boardfarm Config                      │
│     - Get Device By Type, Get Devices By Type                       │
│     - Log Step, Set/Get Test Context, Require Environment           │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│ UseCaseLibrary (Dynamic)                                            │
│   Scope: Test operations                                            │
│   Source: boardfarm3.use_cases modules (cpe, voice, networking...)  │
│   Discovery: Introspects use_case functions at runtime              │
│   Keywords: <Module> <Function>, e.g., "Cpe Get Cpu Usage"          │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Use Cases Instead of Device Methods?

| Approach | Abstraction Level | Example | Maintenance |
|----------|-------------------|---------|-------------|
| Device Methods | Low | `board.sw.get_load_avg()` | Duplicates pytest step defs |
| **Use Cases** | **High** | `get_cpu_usage(board)` | **Single source of truth** |

**Use cases are already documented with test statements they implement:**

```python
# From boardfarm3/use_cases/cpe.py
def get_cpu_usage(board: CPE) -> float:
    """Return the current CPU usage of CPE.

    .. hint:: This Use Case implements statements from the test suite such as:

        - Return the current CPU usage of CPE.
    """
    return board.sw.get_load_avg()
```

### UseCaseLibrary

Introspects Boardfarm use_cases modules:

```robotframework
*** Settings ***
Library    UseCaseLibrary

*** Test Cases ***
Test CPE Performance
    ${cpe}=    Get Device By Type    CPE
    
    # CPE use cases (from boardfarm3/use_cases/cpe.py)
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    ${memory}=    Cpe Get Memory Usage    ${cpe}
    ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
    ${synced}=    Cpe Is Ntp Synchronized    ${cpe}
    
    # Networking use cases (from boardfarm3/use_cases/networking.py)
    ${lan}=    Get Device By Type    LAN
    ${result}=    Networking Ping    ${lan}    8.8.8.8    ping_count=4
    ${dns}=    Networking Dns Lookup    ${lan}    google.com
    
Test Voice Call
    ${phone1}=    Get Device By Type    SIPPhone    index=0
    ${phone2}=    Get Device By Type    SIPPhone    index=1
    
    # Voice use cases (from boardfarm3/use_cases/voice.py)
    Voice Initialize Phone    ${phone1}
    Voice Initialize Phone    ${phone2}
    Voice Call A Phone    ${phone1}    ${phone2}
    ${ringing}=    Voice Is Call Ringing    ${phone2}
    Should Be True    ${ringing}
    Voice Answer A Call    ${phone2}
    ${connected}=    Voice Is Call Connected    ${phone1}
    Should Be True    ${connected}
    Voice Disconnect The Call    ${phone1}
```

### How Dynamic Discovery Works

```python
class UseCaseLibrary:
    """Dynamic library that exposes Boardfarm use_cases as keywords."""
    
    # Modules to introspect
    USE_CASE_MODULES = [
        "boardfarm3.use_cases.cpe",
        "boardfarm3.use_cases.networking",
        "boardfarm3.use_cases.voice",
        "boardfarm3.use_cases.wifi",
        "boardfarm3.use_cases.dhcp",
        "boardfarm3.use_cases.iperf",
        # ... etc
    ]
    
    def get_keyword_names(self):
        keywords = []
        for module_path in self.USE_CASE_MODULES:
            module = importlib.import_module(module_path)
            module_name = module_path.split(".")[-1].title()  # "cpe" -> "Cpe"
            
            for name in dir(module):
                func = getattr(module, name)
                if callable(func) and not name.startswith("_"):
                    # "get_cpu_usage" -> "Cpe Get Cpu Usage"
                    keyword_name = f"{module_name} {self._to_keyword_name(name)}"
                    keywords.append(keyword_name)
                    self._keyword_map[keyword_name] = func
        
        return keywords
    
    def run_keyword(self, name, args, kwargs):
        func = self._keyword_map[name]
        return func(*args, **kwargs)
```

### Handling Boardfarm Updates

When Boardfarm adds new use cases:

| Module | New Function | Robot Framework Keyword |
|--------|--------------|------------------------|
| cpe.py | `get_thermal_status()` | `Cpe Get Thermal Status` |
| networking.py | `traceroute()` | `Networking Traceroute` |
| voice.py | `transfer_call()` | `Voice Transfer Call` |
| wifi.py | `get_signal_strength()` | `Wifi Get Signal Strength` |

**No code changes to robotframework-boardfarm required!**

### Benefits of This Approach

1. **Portability**: pytest step definitions and Robot Framework keywords use the same use_cases
2. **Single Maintenance Point**: Fix a bug in use_cases, both frameworks benefit
3. **Test-Oriented Documentation**: Use cases document which test statements they implement
4. **Consistent Behavior**: Same test logic regardless of framework
5. **Easy Migration**: Moving tests between pytest and Robot Framework is straightforward

---

## Deprecation Handling

### Design Principle: Single Source of Truth

Deprecation warnings are handled **by Boardfarm itself** using the `debtcollector` library, not by the integration layer.

**Why?**
- Avoids duplicate deprecation logic in multiple places
- Ensures consistent warnings for all Boardfarm users (pytest, Robot Framework, direct API)
- When Boardfarm updates deprecations, all integrations automatically get the change
- Follows the principle: handle concerns at the source

### debtcollector Library

Boardfarm uses [debtcollector](https://docs.openstack.org/debtcollector/latest/) (OpenStack library) for deprecation handling. This provides:

- **Standardized deprecation patterns** (moves, renames, removals)
- **Consistent warning messages** via Python's `warnings` module
- **Fixtures for testing** deprecated code paths
- **Well-maintained** by OpenStack community

### How It Works

```
Boardfarm use_case or method (deprecated via debtcollector)
         │
         │ debtcollector emits DeprecationWarning
         ▼
Python warnings module
         │
         ▼
Robot Framework captures warning
         │
         ▼
Appears in test output/log
```

### Deprecation Patterns in Boardfarm use_cases

**1. Function Renamed** (use `debtcollector.moves.moved_function`):

```python
# In Boardfarm (boardfarm3/use_cases/cpe.py)
from debtcollector import moves

def get_cpu_usage(board: CPE) -> float:
    """Return the current CPU usage of CPE."""
    return board.sw.get_load_avg()

# Old function name, now deprecated
get_cpu_load = moves.moved_function(
    get_cpu_usage,
    'get_cpu_load',
    __name__,
    message="Use get_cpu_usage instead"
)
```

**2. Function Removed** (use `debtcollector.removals.remove`):

```python
from debtcollector import removals

@removals.remove(message="This function is no longer supported", removal_version="2.0")
def legacy_reboot(board: CPE) -> None:
    """Deprecated: Use board_reset_via_console instead."""
    board_reset_via_console(board)
```

**3. Argument Renamed** (use `debtcollector.renames.renamed_kwarg`):

```python
from debtcollector import renames

@renames.renamed_kwarg('ping_ip', 'target_ip', version="1.5")
def ping(device, target_ip: str, ping_count: int = 4) -> bool:
    """Ping remote host IP."""
    return device.ping(target_ip, ping_count)
```

**4. Module Moved** (use `debtcollector.moves.moved_module`):

```python
# In old module location
from debtcollector import moves

moves.moved_module(
    'boardfarm3.use_cases.old_module',
    'boardfarm3.use_cases.new_module',
    version="1.5",
    removal_version="2.0"
)
```

### Warning Output in Robot Framework

When a deprecated use_case is called:

```
WARN: DeprecationWarning: get_cpu_load is deprecated. Use get_cpu_usage instead.
      It will be removed in version 2.0.
```

### Boardfarm Responsibilities

Boardfarm should:

1. **Add debtcollector as a dependency** in `pyproject.toml`:
   ```toml
   dependencies = [
       "debtcollector>=3.0.0",
       # ... other deps
   ]
   ```

2. **Use debtcollector decorators/helpers** to mark deprecated code:
   - `moves.moved_function` - for renamed functions
   - `removals.remove` - for functions being removed
   - `renames.renamed_kwarg` - for renamed arguments
   - `moves.moved_class` - for renamed classes
   - `moves.moved_module` - for moved modules

3. **Specify removal versions** to give users advance warning

4. **Document deprecations** in CHANGELOG and release notes

### robotframework-boardfarm Role

The integration layer simply:
- **Passes through** whatever warnings debtcollector emits
- **Does not** implement its own deprecation detection
- **Does not** maintain separate deprecation state

This keeps the integration simple and ensures users get the same experience regardless of how they use Boardfarm.

### Testing Deprecated Code

debtcollector provides fixtures for testing that deprecated code still works while emitting warnings:

```python
# In Boardfarm tests
from debtcollector import fixtures

class TestDeprecatedUseCases:
    def test_old_function_still_works(self):
        """Verify deprecated function works but emits warning."""
        with fixtures.WarningsFixture() as capture:
            result = get_cpu_load(board)  # Deprecated, calls get_cpu_usage
            assert result > 0
            assert len(capture) == 1
            assert "get_cpu_load is deprecated" in str(capture[0].message)
```

---

## Implementation Phases

### Phase 1: Project Foundation (1-2 days)

**Goal**: Establish project structure, dependencies, and basic infrastructure.

**Deliverables**:
- [ ] Project structure with `pyproject.toml`
- [ ] Basic package layout
- [ ] Development tooling configuration (ruff, mypy, pytest)
- [ ] README with overview and goals
- [ ] CI/CD configuration (GitHub Actions)

**Files to Create**:
```
robotframework-boardfarm/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
├── .flake8
├── .pylintrc
├── noxfile.py
├── robotframework_boardfarm/
│   ├── __init__.py
│   ├── py.typed
│   └── version.py
└── tests/
    └── __init__.py
```

### Phase 2: Listener Implementation (2-3 days)

**Goal**: Implement the core lifecycle management listener.

**Deliverables**:
- [ ] `BoardfarmListener` class implementing Listener API v3
- [ ] Suite-level device deployment/teardown
- [ ] Test-level contingency checks
- [ ] Logging integration
- [ ] Error handling and recovery

**Key Methods**:
```python
class BoardfarmListener:
    ROBOT_LISTENER_API_VERSION = 3
    
    def start_suite(self, data, result):
        """Deploy boardfarm devices at suite start."""
        
    def end_suite(self, data, result):
        """Release boardfarm devices at suite end."""
        
    def start_test(self, data, result):
        """Validate env requirements and run contingency checks."""
        
    def end_test(self, data, result):
        """Cleanup and capture logs."""
```

### Phase 3: Keyword Libraries (2-3 days)

**Goal**: Create keyword libraries for testbed access and use case operations.

**Deliverables**:
- [ ] `BoardfarmLibrary` - Infrastructure keywords for device/config access
- [ ] `UseCaseLibrary` - Dynamic library introspecting Boardfarm use_cases
- [ ] Documentation auto-generated from use_case docstrings

**BoardfarmLibrary Keywords** (static infrastructure keywords):
```robotframework
# Device access
Get Device By Type    ${device_type}    # Resolves type from string
Get Devices By Type   ${device_type}
Get Device Manager

# Configuration access
Get Boardfarm Config
Get Device Config    ${device_name}
Get Provisioning Mode
Get Board Sku

# Test utilities (Robot Framework specific)
Log Step    ${message}
Set Test Context    ${key}    ${value}
Get Test Context    ${key}
Clear Test Context
Require Environment    ${requirement}
```

**UseCaseLibrary Keywords** (dynamically discovered from boardfarm3.use_cases):
```robotframework
# From use_cases/cpe.py
Cpe Get Cpu Usage           ${board}
Cpe Get Memory Usage        ${board}
Cpe Get Seconds Uptime      ${board}
Cpe Is Ntp Synchronized     ${board}
Cpe Is Tr069 Agent Running  ${board}
Cpe Factory Reset           ${board}    method=${None}
Cpe Board Reset Via Console ${board}
Cpe Enable Logs             ${board}    ${component}
Cpe Disable Logs            ${board}    ${component}

# From use_cases/networking.py
Networking Ping             ${device}    ${ping_ip}    ping_count=4
Networking Http Get         ${device}    ${url}
Networking Dns Lookup       ${host}      ${domain_name}
Networking Create Tcp Session  ${source}  ${dest}  ${ip_type}  ${port}
Networking Enable Ipv6      ${device}
Networking Disable Ipv6     ${device}

# From use_cases/voice.py
Voice Call A Phone          ${caller}    ${callee}
Voice Answer A Call         ${who_answers}
Voice Disconnect The Call   ${who_disconnects}
Voice Is Call Connected     ${who_is_connected}
Voice Is Call Ringing       ${who_is_ringing}
Voice Initialize Phone      ${target_phone}
Voice Shutdown Phone        ${target_phone}
Voice Place Call Onhold     ${who_places}
Voice Merge Two Calls       ${who_is_conferencing}

# From use_cases/wifi.py, dhcp.py, iperf.py, etc.
# ... all functions auto-discovered
```

### Phase 4: Configuration & CLI Integration (1-2 days)

**Goal**: Handle configuration loading and command-line arguments.

**Deliverables**:
- [ ] Variable file for Robot Framework
- [ ] Argument forwarding to Boardfarm hooks
- [ ] Config validation and merging
- [ ] Pre-run modifier for test filtering

**Usage Pattern**:
```bash
robot --listener robotframework_boardfarm.BoardfarmListener \
      --variable BOARD_NAME:prplos-docker-1 \
      --variable ENV_CONFIG:./bf_config/boardfarm_env.json \
      --variable INVENTORY_CONFIG:./bf_config/boardfarm_config.json \
      --variablefile robotframework_boardfarm/variables.py \
      tests/
```

### Phase 5: Environment Requirement Support (1-2 days)

**Goal**: Implement tag-based environment filtering (equivalent to `@pytest.mark.env_req`).

**Deliverables**:
- [ ] Pre-run modifier for `env_req` tag parsing
- [ ] Environment matching logic (port from pytest-boardfarm)
- [ ] Test skipping for incompatible environments
- [ ] Documentation on tag syntax

**Tag Syntax**:
```robotframework
*** Test Cases ***
Test Dual Stack Mode
    [Tags]    env_req:{"environment_def":{"board":{"eRouter_Provisioning_mode":["dual"]}}}
    # Test implementation
```

### Phase 6: Reporting Integration (1-2 days)

**Goal**: Enhance Robot Framework reports with Boardfarm information.

**Deliverables**:
- [ ] Result visitor for report enhancement
- [ ] Deployment status in report
- [ ] Device information in report
- [ ] Console log attachments
- [ ] Screenshot support

### Phase 7: Testing & Documentation (2-3 days)

**Goal**: Comprehensive testing and documentation.

**Deliverables**:
- [ ] Unit tests for all components
- [ ] Integration tests with mock devices
- [ ] Example test suites
- [ ] API documentation
- [ ] User guide
- [ ] Migration guide (from pytest to Robot Framework)

### Phase 8: Validation & Refinement (2-3 days)

**Goal**: Test against real testbed and refine based on feedback.

**Deliverables**:
- [ ] Execute existing BDD scenarios ported to Robot Framework
- [ ] Performance benchmarking
- [ ] Error message improvements
- [ ] Edge case handling
- [ ] Final documentation polish

---

## Detailed Component Specifications

### 1. BoardfarmListener

```python
"""Robot Framework listener for Boardfarm integration."""

from __future__ import annotations

import asyncio
import logging
from argparse import Namespace
from typing import TYPE_CHECKING, Any

from boardfarm3.lib.boardfarm_config import BoardfarmConfig, get_json
from boardfarm3.lib.device_manager import DeviceManager
from boardfarm3.main import get_plugin_manager

if TYPE_CHECKING:
    from robot.running import TestSuite, TestCase
    from robot.result import TestSuite as ResultSuite, TestCase as ResultCase


class BoardfarmListener:
    """Robot Framework listener for Boardfarm device lifecycle management."""

    ROBOT_LISTENER_API_VERSION = 3
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(
        self,
        board_name: str | None = None,
        env_config: str | None = None,
        inventory_config: str | None = None,
        skip_boot: bool = False,
        skip_contingency_checks: bool = False,
        save_console_logs: str | None = None,
    ) -> None:
        """Initialize boardfarm listener.

        Args:
            board_name: Name of the board to use
            env_config: Path to environment JSON config
            inventory_config: Path to inventory JSON config
            skip_boot: Skip device booting if True
            skip_contingency_checks: Skip contingency checks if True
            save_console_logs: Path to save console logs
        """
        self._board_name = board_name
        self._env_config_path = env_config
        self._inventory_config_path = inventory_config
        self._skip_boot = skip_boot
        self._skip_contingency_checks = skip_contingency_checks
        self._save_console_logs = save_console_logs

        self._plugin_manager = get_plugin_manager()
        self._device_manager: DeviceManager | None = None
        self._boardfarm_config: BoardfarmConfig | None = None
        self._deployment_data: dict[str, Any] = {}
        self._logger = logging.getLogger("boardfarm.robotframework")

    @property
    def device_manager(self) -> DeviceManager:
        """Return device manager instance."""
        if self._device_manager is None:
            raise RuntimeError("Device manager not initialized")
        return self._device_manager

    @property
    def boardfarm_config(self) -> BoardfarmConfig:
        """Return boardfarm config instance."""
        if self._boardfarm_config is None:
            raise RuntimeError("Boardfarm config not initialized")
        return self._boardfarm_config

    def start_suite(self, data: TestSuite, result: ResultSuite) -> None:
        """Deploy boardfarm devices at suite start.

        Only deploys for the root suite (top-level).
        """
        if data.parent is None:  # Root suite only
            self._deploy_devices()

    def end_suite(self, data: TestSuite, result: ResultSuite) -> None:
        """Release boardfarm devices at suite end.

        Only releases for the root suite (top-level).
        """
        if data.parent is None:  # Root suite only
            self._release_devices()

    def start_test(self, data: TestCase, result: ResultCase) -> None:
        """Validate environment requirements before test execution."""
        if not self._skip_contingency_checks:
            env_req = self._parse_env_req_tags(data.tags)
            if env_req:
                self._validate_env_requirement(env_req)

    def end_test(self, data: TestCase, result: ResultCase) -> None:
        """Cleanup after test execution."""
        pass  # Future: capture logs, cleanup context

    def _deploy_devices(self) -> None:
        """Deploy boardfarm devices."""
        # Implementation follows pytest-boardfarm pattern
        ...

    def _release_devices(self) -> None:
        """Release boardfarm devices."""
        # Implementation follows pytest-boardfarm pattern
        ...

    def _parse_env_req_tags(self, tags: list[str]) -> dict[str, Any] | None:
        """Parse env_req tags from test tags."""
        ...

    def _validate_env_requirement(self, env_req: dict[str, Any]) -> None:
        """Validate environment meets test requirements."""
        ...
```

### 2. BoardfarmLibrary

```python
"""Robot Framework keyword library for Boardfarm infrastructure access.

Provides static keywords for device access, configuration, and test utilities.
Does NOT expose device methods directly - use UseCaseLibrary for test operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from robot.api import logger
from robot.api.deco import keyword, library

if TYPE_CHECKING:
    from boardfarm3.lib.boardfarm_config import BoardfarmConfig
    from boardfarm3.lib.device_manager import DeviceManager


@library(scope="GLOBAL", version="0.1.0")
class BoardfarmLibrary:
    """Infrastructure library for Boardfarm testbed access.

    Provides keywords for:
    - Device access (get devices by type)
    - Configuration access (boardfarm config, device config)
    - Test utilities (logging, context management, environment requirements)

    Example:
        | *** Settings ***
        | Library    BoardfarmLibrary
        |
        | *** Test Cases ***
        | Test Device Access
        |     ${cpe}=    Get Device By Type    CPE
        |     ${mode}=    Get Provisioning Mode
        |     Log Step    CPE is in ${mode} mode
    """

    def __init__(self) -> None:
        self._context: dict[str, Any] = {}

    # === Device Access Keywords ===

    @keyword("Get Device By Type")
    def get_device_by_type(self, device_type: str, index: int = 0):
        """Get device by type name.
        
        Args:
            device_type: Type name (e.g., "CPE", "LAN", "ACS", "SIPPhone")
            index: Index if multiple devices of same type (default: 0)
        """
        ...

    @keyword("Get Devices By Type")
    def get_devices_by_type(self, device_type: str) -> dict:
        """Get all devices of a specific type."""
        ...

    @keyword("Get Device Manager")
    def get_device_manager(self):
        """Get the DeviceManager instance for advanced access."""
        ...

    # === Configuration Keywords ===

    @keyword("Get Boardfarm Config")
    def get_boardfarm_config(self):
        """Get the BoardfarmConfig instance."""
        ...

    @keyword("Get Device Config")
    def get_device_config(self, device_name: str) -> dict:
        """Get configuration for a specific device."""
        ...

    @keyword("Get Provisioning Mode")
    def get_provisioning_mode(self) -> str:
        """Get the provisioning mode (dual, ipv4, ipv6)."""
        ...

    @keyword("Get Board Sku")
    def get_board_sku(self) -> str:
        """Get the board SKU."""
        ...

    # === Test Utility Keywords ===

    @keyword("Log Step")
    def log_step(self, message: str) -> None:
        """Log a test step message."""
        logger.info(f"[STEP] {message}", html=False)

    @keyword("Set Test Context")
    def set_test_context(self, key: str, value: Any) -> None:
        """Store a value in the test context."""
        self._context[key] = value

    @keyword("Get Test Context")
    def get_test_context(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the test context."""
        return self._context.get(key, default)

    @keyword("Clear Test Context")
    def clear_test_context(self) -> None:
        """Clear all values from the test context."""
        self._context.clear()

    @keyword("Require Environment")
    def require_environment(self, requirement: str | dict) -> None:
        """Assert environment meets requirement or skip test.
        
        Args:
            requirement: Preset name (e.g., "dual_stack") or dict with requirements
        """
        from robot.api import SkipExecution
        if not self._check_env_requirement(requirement):
            raise SkipExecution(f"Environment requirement not met: {requirement}")
```

### 3. UseCaseLibrary (Dynamic)

```python
"""Dynamic library that exposes Boardfarm use_cases as Robot Framework keywords.

Introspects boardfarm3.use_cases modules to automatically discover and expose
functions as keywords. This provides a single source of truth for test operations.

Key Benefits:
- Same use cases work for pytest-boardfarm and robotframework-boardfarm
- No duplication of test logic between frameworks
- Automatic discovery of new use cases when Boardfarm is updated
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any


class UseCaseLibrary:
    """Dynamic library that exposes Boardfarm use_cases as keywords.

    Introspects boardfarm3.use_cases modules at runtime to discover
    functions and expose them as Robot Framework keywords.

    Example:
        | *** Settings ***
        | Library    UseCaseLibrary
        |
        | *** Test Cases ***
        | Test CPE Operations
        |     ${cpe}=    Get Device By Type    CPE
        |     ${cpu}=    Cpe Get Cpu Usage    ${cpe}
        |     ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
        |
        | Test Voice Call
        |     ${phone1}=    Get Device By Type    SIPPhone    index=0
        |     ${phone2}=    Get Device By Type    SIPPhone    index=1
        |     Voice Call A Phone    ${phone1}    ${phone2}
        |     Voice Answer A Call    ${phone2}
        |     ${connected}=    Voice Is Call Connected    ${phone1}
        |     Should Be True    ${connected}
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    # Modules to introspect for use case functions
    USE_CASE_MODULES = [
        "boardfarm3.use_cases.cpe",
        "boardfarm3.use_cases.networking",
        "boardfarm3.use_cases.voice",
        "boardfarm3.use_cases.wifi",
        "boardfarm3.use_cases.dhcp",
        "boardfarm3.use_cases.iperf",
        "boardfarm3.use_cases.device_getters",
        "boardfarm3.use_cases.device_utilities",
        "boardfarm3.use_cases.multicast",
        "boardfarm3.use_cases.ripv2",
        "boardfarm3.use_cases.image_comparison",
    ]

    def __init__(self) -> None:
        self._keyword_map: dict[str, tuple[Any, str]] = {}  # keyword -> (func, doc)
        self._discovered = False

    def get_keyword_names(self) -> list[str]:
        """Discover keywords from use_cases modules."""
        if not self._discovered:
            self._discover_keywords()
        return list(self._keyword_map.keys())

    def get_keyword_documentation(self, name: str) -> str:
        """Return documentation for a keyword."""
        if name in self._keyword_map:
            func, _ = self._keyword_map[name]
            return func.__doc__ or ""
        return ""

    def get_keyword_arguments(self, name: str) -> list[str]:
        """Return argument specification for a keyword."""
        if name in self._keyword_map:
            func, _ = self._keyword_map[name]
            sig = inspect.signature(func)
            args = []
            for param_name, param in sig.parameters.items():
                if param.default is inspect.Parameter.empty:
                    args.append(param_name)
                else:
                    args.append(f"{param_name}={param.default!r}")
            return args
        return []

    def run_keyword(self, name: str, args: list, kwargs: dict) -> Any:
        """Execute a use case keyword."""
        if name not in self._keyword_map:
            raise ValueError(f"Unknown keyword: {name}")
        
        func, _ = self._keyword_map[name]
        return func(*args, **kwargs)

    def _discover_keywords(self) -> None:
        """Discover functions from use_cases modules."""
        for module_path in self.USE_CASE_MODULES:
            try:
                module = importlib.import_module(module_path)
            except ImportError:
                continue  # Module not available
            
            # Extract module name for prefix: "boardfarm3.use_cases.cpe" -> "Cpe"
            module_name = module_path.split(".")[-1]
            prefix = module_name.replace("_", " ").title().replace(" ", "")
            
            for name in dir(module):
                if name.startswith("_"):
                    continue
                
                func = getattr(module, name)
                if not callable(func) or isinstance(func, type):
                    continue
                
                # Skip imported items (only include functions defined in this module)
                if hasattr(func, "__module__") and func.__module__ != module_path:
                    continue
                
                # Convert function name to keyword: "get_cpu_usage" -> "Get Cpu Usage"
                keyword_suffix = name.replace("_", " ").title()
                keyword_name = f"{prefix} {keyword_suffix}"
                
                self._keyword_map[keyword_name] = (func, func.__doc__ or "")
        
        self._discovered = True

    @staticmethod
    def _to_keyword_name(func_name: str) -> str:
        """Convert function name to keyword name."""
        return func_name.replace("_", " ").title()
```

### 4. Variable File

```python
"""Robot Framework variable file for Boardfarm configuration."""

import os
from typing import Any


def get_variables(
    board_name: str | None = None,
    env_config: str | None = None,
    inventory_config: str | None = None,
) -> dict[str, Any]:
    """Return variables for Robot Framework.

    Variables can be overridden via command line:
        robot --variable BOARD_NAME:my-board tests/

    Args:
        board_name: Board name (can be set via BOARD_NAME env var)
        env_config: Environment config path
        inventory_config: Inventory config path

    Returns:
        Dictionary of variables for Robot Framework.
    """
    return {
        "BOARD_NAME": board_name or os.environ.get("BOARD_NAME", ""),
        "ENV_CONFIG": env_config or os.environ.get("ENV_CONFIG", ""),
        "INVENTORY_CONFIG": inventory_config or os.environ.get("INVENTORY_CONFIG", ""),
        "SKIP_BOOT": os.environ.get("SKIP_BOOT", "false").lower() == "true",
        "SKIP_CONTINGENCY_CHECKS": os.environ.get(
            "SKIP_CONTINGENCY_CHECKS", "false"
        ).lower() == "true",
    }
```

---

## Usage Examples

### Basic Test Suite

```robotframework
*** Settings ***
Library           BoardfarmLibrary
Library           UseCaseLibrary
Suite Setup       Log    Starting Boardfarm tests
Suite Teardown    Log    Completed Boardfarm tests

*** Test Cases ***
Test Device Connection
    [Documentation]    Verify device connectivity
    ${cpe}=    Get Device By Type    CPE
    Log    Connected to CPE: ${cpe}
    ${uptime}=    Cpe Get Seconds Uptime    ${cpe}
    Log    CPE uptime: ${uptime} seconds

Test Provisioning Mode
    [Documentation]    Verify provisioning mode
    ${mode}=    Get Provisioning Mode
    Log    Provisioning mode: ${mode}
    Should Be Equal    ${mode}    dual

Test CPE Performance
    [Documentation]    Check CPE performance metrics
    ${cpe}=    Get Device By Type    CPE
    ${cpu}=    Cpe Get Cpu Usage    ${cpe}
    ${memory}=    Cpe Get Memory Usage    ${cpe}
    Log Step    CPU: ${cpu}%, Memory: ${memory}
    Should Be True    ${cpu} < 90    CPU usage too high

Test With Environment Requirement
    [Documentation]    Test requiring dual stack
    [Tags]    env_req:dual_stack
    Require Environment    dual_stack
    Log Step    Environment validated
    ${cpe}=    Get Device By Type    CPE
    ${mode}=    Cpe Get Cpe Provisioning Mode    ${cpe}
    Should Be Equal    ${mode}    dual
```

### Networking Test Suite

```robotframework
*** Settings ***
Library           BoardfarmLibrary
Library           UseCaseLibrary

*** Test Cases ***
Test LAN Connectivity
    [Documentation]    Verify LAN client can ping external host
    ${lan}=    Get Device By Type    LAN
    ${result}=    Networking Ping    ${lan}    8.8.8.8    ping_count=4
    Should Be True    ${result}    Ping failed

Test DNS Resolution
    [Documentation]    Verify DNS is working
    ${lan}=    Get Device By Type    LAN
    ${dns_result}=    Networking Dns Lookup    ${lan}    google.com
    Should Not Be Empty    ${dns_result}

Test HTTP Access
    [Documentation]    Verify HTTP access works
    ${lan}=    Get Device By Type    LAN
    ${http_result}=    Networking Http Get    ${lan}    http://example.com
    Log    HTTP response: ${http_result}
```

### Voice Test Suite

```robotframework
*** Settings ***
Library           BoardfarmLibrary
Library           UseCaseLibrary
Test Setup        Initialize Phones
Test Teardown     Shutdown Phones

*** Variables ***
${PHONE1}         ${EMPTY}
${PHONE2}         ${EMPTY}

*** Keywords ***
Initialize Phones
    ${phone1}=    Get Device By Type    SIPPhone    index=0
    ${phone2}=    Get Device By Type    SIPPhone    index=1
    Set Suite Variable    ${PHONE1}    ${phone1}
    Set Suite Variable    ${PHONE2}    ${phone2}
    Voice Initialize Phone    ${PHONE1}
    Voice Initialize Phone    ${PHONE2}

Shutdown Phones
    Voice Shutdown Phone    ${PHONE1}
    Voice Shutdown Phone    ${PHONE2}

*** Test Cases ***
Test Basic Voice Call
    [Documentation]    Verify basic voice call establishment
    # Phone 1 calls Phone 2
    Voice Call A Phone    ${PHONE1}    ${PHONE2}
    
    # Phone 2 should be ringing
    ${ringing}=    Voice Is Call Ringing    ${PHONE2}
    Should Be True    ${ringing}    Phone 2 is not ringing
    
    # Phone 2 answers
    Voice Answer A Call    ${PHONE2}
    
    # Both phones should be connected
    ${connected1}=    Voice Is Call Connected    ${PHONE1}
    ${connected2}=    Voice Is Call Connected    ${PHONE2}
    Should Be True    ${connected1}    Phone 1 not connected
    Should Be True    ${connected2}    Phone 2 not connected
    
    # Phone 1 hangs up
    Voice Disconnect The Call    ${PHONE1}
    
    # Call should be ended
    ${ended}=    Voice Is Call Ended    ${PHONE2}
    Should Be True    ${ended}    Call not properly ended

Test Call On Hold
    [Documentation]    Verify call can be placed on hold
    Voice Call A Phone    ${PHONE1}    ${PHONE2}
    Voice Answer A Call    ${PHONE2}
    
    # Place call on hold
    Voice Place Call Onhold    ${PHONE1}
    ${onhold}=    Voice Is Call On Hold    ${PHONE1}
    Should Be True    ${onhold}    Call not on hold
    
    # Take call off hold
    Voice Place Call Offhold    ${PHONE1}
    ${connected}=    Voice Is Call Connected    ${PHONE1}
    Should Be True    ${connected}    Call not reconnected
    
    Voice Disconnect The Call    ${PHONE1}
```

### Command Line Execution

```bash
# Basic execution
robot --listener robotframework_boardfarm.BoardfarmListener:board_name=prplos-docker-1:env_config=./bf_config/boardfarm_env.json:inventory_config=./bf_config/boardfarm_config.json \
      tests/

# Using variables
robot --variable BOARD_NAME:prplos-docker-1 \
      --variable ENV_CONFIG:./bf_config/boardfarm_env.json \
      --variable INVENTORY_CONFIG:./bf_config/boardfarm_config.json \
      --listener robotframework_boardfarm.BoardfarmListener \
      tests/

# Skip boot for faster iteration
robot --variable SKIP_BOOT:true \
      --listener robotframework_boardfarm.BoardfarmListener \
      tests/
```

---

## Dependencies

### robotframework-boardfarm

```toml
[project]
dependencies = [
    "robotframework>=6.0",
    "boardfarm3>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",
    "mypy",
    "pre-commit",
]
```

### Boardfarm (boardfarm3)

Boardfarm should include `debtcollector` for deprecation handling:

```toml
[project]
dependencies = [
    "debtcollector>=3.0.0",  # For deprecation handling
    # ... other existing dependencies
]
```

**Note**: `debtcollector` is a dependency of Boardfarm, not robotframework-boardfarm. The integration layer simply passes through deprecation warnings emitted by Boardfarm.

---

## Framework Portability

### Shared Use Cases Between pytest and Robot Framework

The use case-based approach enables seamless test logic sharing:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Boardfarm use_cases                              │
│            (Single Source of Truth for Test Logic)                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   pytest-boardfarm    │       │ robotframework-boardfarm│
│                       │       │                       │
│ @given("CPU usage")   │       │ Cpe Get Cpu Usage     │
│ def step():           │       │     ${board}          │
│   cpu = get_cpu_usage │       │                       │
│         (board)       │       │ (calls same function) │
└───────────────────────┘       └───────────────────────┘
```

### Example: Same Test in Both Frameworks

**pytest-bdd (boardfarm-bdd):**
```python
# tests/step_defs/cpe_steps.py
from boardfarm3.use_cases.cpe import get_cpu_usage, get_memory_usage

@given("I check the CPE performance")
def check_cpe_performance(bf_context):
    board = bf_context.device_manager.get_device_by_type(CPE)
    cpu = get_cpu_usage(board)
    memory = get_memory_usage(board)
    bf_context.cpu_usage = cpu
    bf_context.memory_usage = memory

@then("the CPU usage should be below {threshold}%")
def verify_cpu_usage(bf_context, threshold):
    assert bf_context.cpu_usage < float(threshold)
```

**Robot Framework (robotframework-boardfarm):**
```robotframework
*** Test Cases ***
Test CPE Performance
    ${board}=    Get Device By Type    CPE
    ${cpu}=    Cpe Get Cpu Usage    ${board}
    ${memory}=    Cpe Get Memory Usage    ${board}
    Should Be True    ${cpu} < 90    CPU usage too high
```

**Both call the exact same Boardfarm use_case function!**

### Migration Path

Moving tests between frameworks is straightforward because the business logic stays in Boardfarm:

| pytest step | Robot Framework keyword |
|-------------|------------------------|
| `get_cpu_usage(board)` | `Cpe Get Cpu Usage    ${board}` |
| `ping(device, ip)` | `Networking Ping    ${device}    ${ip}` |
| `call_a_phone(caller, callee)` | `Voice Call A Phone    ${caller}    ${callee}` |

---

## Testing Strategy

### Unit Tests
- Test listener lifecycle methods with mocked Boardfarm
- Test keyword library with mocked use_cases
- Test configuration loading and merging
- Test environment matching logic
- Test keyword discovery from use_cases modules

### Integration Tests
- Test with mock devices (no real hardware)
- Verify listener/library interaction
- Test error handling and recovery
- Verify use_case keyword arguments are correctly passed

### System Tests
- Execute against real testbed
- Port existing BDD scenarios to Robot Framework
- Verify report generation
- Compare results with pytest-boardfarm execution

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Foundation | 1-2 days | None |
| Phase 2: Listener | 2-3 days | Phase 1 |
| Phase 3: Keywords | 2-3 days | Phase 2 |
| Phase 4: Configuration | 1-2 days | Phase 2 |
| Phase 5: Env Requirements | 1-2 days | Phase 3, 4 |
| Phase 6: Reporting | 1-2 days | Phase 3 |
| Phase 7: Testing/Docs | 2-3 days | All |
| Phase 8: Validation | 2-3 days | Phase 7 |

**Total Estimated Duration**: 12-20 days

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Async operations in Robot Framework | Medium | Use `asyncio.run()` wrapper, test thoroughly |
| Device state persistence across tests | High | Clear state in listener hooks, document cleanup |
| Report customization limitations | Low | Use result visitors, custom log messages |
| Performance overhead | Medium | Lazy initialization, caching |
| Use case API changes | Low | Dynamic discovery adapts automatically |
| Missing use cases for some operations | Medium | Can still access device methods directly via BoardfarmLibrary |

---

## Success Criteria

1. ✅ Execute existing Boardfarm test scenarios in Robot Framework
2. ✅ Device deployment and teardown works reliably
3. ✅ Environment requirements filter tests correctly
4. ✅ Reports include Boardfarm deployment information
5. ✅ Documentation enables self-service adoption
6. ✅ Performance comparable to pytest-boardfarm
7. ✅ **Use case keywords match pytest step definitions** (portability)
8. ✅ **No duplication of test logic** (single source of truth)

---

## Next Steps

1. Create project structure (Phase 1)
2. Implement core listener (Phase 2)
3. Iterate on keyword library based on usage patterns
4. Validate with real testbed scenarios

---

## Change Log

### Version 2.0 (January 25, 2026)

**Major Architecture Change**: Shifted abstraction level from device methods to Boardfarm use_cases.

**Key Changes**:
- Replaced `DeviceMethodLibrary` with `UseCaseLibrary`
- Keywords now map to `boardfarm3.use_cases` module functions
- Added abstraction layer diagram showing 4-layer architecture
- Updated all code examples to use use_case keywords
- Added Framework Portability section showing pytest/Robot Framework equivalence
- Added Voice and Networking test suite examples
- Updated success criteria to include portability and single source of truth
- **Updated deprecation handling to use `debtcollector` library** (OpenStack standard)
- Added comprehensive debtcollector patterns (moves, renames, removals)
- Added testing examples for deprecated code paths

**Benefits**:
- Single source of truth: Test logic lives in Boardfarm, not integration layer
- Portability: Same use cases work for pytest-boardfarm and robotframework-boardfarm
- Maintainability: No duplication of test logic between frameworks
- Documentation: Use cases already document which test statements they implement
- Standardized deprecation: debtcollector provides consistent, well-tested patterns

### Version 1.0 (January 17, 2025)

- Initial development plan
- Device method-based keyword discovery
- Basic architecture and implementation phases

---

**Document Version**: 2.0  
**Last Updated**: January 25, 2026
