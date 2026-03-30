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

### Using bfrobot CLI (Recommended)

```bash
bfrobot --board-name prplos-docker-1 \
        --env-config ./bf_config/boardfarm_env.json \
        --inventory-config ./bf_config/boardfarm_config.json \
        examples/basic_test.robot
```

### Using Direct Listener

```bash
robot --listener "robotframework_boardfarm.BoardfarmListener:\
board_name=prplos-docker-1:\
env_config=./bf_config/boardfarm_env.json:\
inventory_config=./bf_config/boardfarm_config.json" \
      examples/basic_test.robot
```

### Skip Boot Mode (Development)

For faster iteration during development, skip device boot:

```bash
bfrobot --board-name my-board \
        --env-config ./env.json \
        --inventory-config ./inv.json \
        --skip-boot \
        examples/basic_test.robot
```

## Example Files

| File | Description |
|------|-------------|
| `basic_test.robot` | Basic device and config access |
| `env_requirement_test.robot` | Environment requirement examples |

## Recommended Approach: Keyword Libraries

For comprehensive test suites, create **scenario-aligned keyword libraries**
in your test project that delegate to `boardfarm3.use_cases`.

### Key Principles

1. **Libraries are the single source of truth** — Define all keywords in `robot/libraries/*.py`
2. **Tests contain no keyword definitions** — Test files call library keywords directly
3. **Libraries are thin wrappers** — Delegate to `boardfarm3.use_cases`
4. **Cleanup is automatic** — State-changing keywords call `register_teardown()` to push
   a reverse action onto the listener's per-test stack; the stack is drained in LIFO order
   when the test ends

This approach:
- Mirrors pytest-bdd step_defs structure (keyword ↔ step_def, `register_teardown` ↔ `yield`)
- Uses `@keyword` decorator for clean Python-to-keyword mapping
- Maintains single source of truth in `boardfarm3.use_cases`
- Avoids duplication, naming conflicts, and manual `[Teardown]` in `.robot` files

See the [boardfarm-bdd/robot/libraries/](../../boardfarm-bdd/robot/libraries/) directory
for a complete example of this pattern.

### Example Keyword Library (with teardown registration)

```python
# robot/libraries/acs_keywords.py
import logging
from robot.api.deco import keyword
from boardfarm3.use_cases import acs as acs_use_cases

_LOGGER = logging.getLogger(__name__)


def _get_listener():
    from robotframework_boardfarm.listener import get_listener
    return get_listener()


class AcsKeywords:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    @keyword("The CPE is online via ACS")
    def verify_cpe_online(self, acs, cpe):
        """Verify CPE connectivity via ACS."""
        return acs_use_cases.is_cpe_online(acs, cpe)

    @keyword("The operator sets a CPE parameter")
    def set_parameter(self, acs, cpe, path, value):
        """Set a TR-069 parameter and auto-register restoration."""
        original = acs_use_cases.get_parameter_value(acs, cpe, path)
        acs_use_cases.set_parameter_value(acs, cpe, path, value)

        try:
            _get_listener().register_teardown(
                f"Restore {path}",
                acs_use_cases.set_parameter_value,
                acs, cpe, path, original,
            )
        except Exception:
            _LOGGER.debug("Listener unavailable; skipping teardown registration")
```

### Example Test Using Keyword Library

```robot
*** Settings ***
Library    robotframework_boardfarm.BoardfarmLibrary
Library    ../libraries/acs_keywords.py

*** Test Cases ***
Test CPE Online
    [Documentation]    No [Teardown] needed — the listener handles cleanup.
    ${acs}=    Get Device By Type    ACS
    ${cpe}=    Get Device By Type    CPE
    The CPE Is Online Via ACS    ${acs}    ${cpe}
```

## Environment Requirements

Use tags for environment requirements:

```robot
*** Test Cases ***
Test Dual Stack
    [Tags]    env_req:dual_stack
    # Test only runs in dual stack environments
```

Or use the keyword:

```robot
*** Test Cases ***
Test With Requirement
    Require Environment    dual_stack
    # Test continues only if requirement is met
```
