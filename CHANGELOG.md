# Changelog

All notable changes to `robotframework-boardfarm` are documented in this file.

## 0.3.0 (March 26, 2026)

### Added

- **Per-test teardown stack** — `BoardfarmListener.register_teardown(description, func, *args, **kwargs)` pushes a cleanup action onto a per-test stack. `end_test()` drains the stack in LIFO order, bringing Robot Framework cleanup to parity with pytest-bdd's `yield`-based teardown.
- **CPE console refresh** — `end_test()` disconnects and reconnects the CPE console after every test, ensuring a clean state for the next test.
- **Per-test library context clearing** — `end_test()` calls `clear_test_context()` on `BoardfarmLibrary` after every test.
- **`get_listener()` accessor** — module-level function for keyword libraries to obtain the active `BoardfarmListener` instance.

### Changed

- `BoardfarmListener.end_test()` now executes three phases: drain teardown stack, refresh CPE console, clear library context. Previously it was a no-op.

## 0.2.0 (January 29, 2026)

### Removed

- **`UseCaseLibrary`** — Keywords should be created in the test project's `robot/libraries/` directory.
- **`DeviceMethodLibrary`** — Keyword libraries have direct access to device objects.

### Changed

- Simplified to minimal footprint: `BoardfarmListener` (lifecycle), `BoardfarmLibrary` (infrastructure keywords), and `bfrobot` CLI.

## 0.1.0 (January 25, 2026)

### Added

- Initial implementation with `BoardfarmListener`, `BoardfarmLibrary`, `UseCaseLibrary`, `DeviceMethodLibrary`, and `bfrobot` CLI.
