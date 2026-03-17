"""Utility functions for robotframework-boardfarm.

This module contains shared utilities, primarily ported from pytest-boardfarm
to maintain compatibility.
"""

from __future__ import annotations

import re
from typing import Any


def _perform_contains_check(
    test_env_request: list[dict[str, str]],
    boardfarm_env: str,
) -> bool:
    """Perform contains checks on environment string.

    Args:
        test_env_request: List of contains check dictionaries
        boardfarm_env: Environment string to check

    Returns:
        True if all checks pass, False otherwise.

    Raises:
        ValueError: If invalid check type is provided.
    """
    checks_dict: dict[str, Any] = {
        "contains_exact": lambda value, env_req: value in env_req,
        "not_contains_exact": lambda value, env_req: value not in env_req,
        "contains_regex": re.search,
        "not_contains_regex": lambda value, env_req: not re.search(value, env_req),
    }

    invalid_checks = {
        next(iter(item.keys()))
        for item in test_env_request
        if next(iter(item.keys())) not in checks_dict
    }
    if invalid_checks:
        msg = f"Invalid contains checks: {invalid_checks}"
        raise ValueError(msg)

    for contains_check in test_env_request:
        check, value = next(iter(contains_check.items()))
        if not checks_dict[check](value, boardfarm_env):
            return False
    return True


def is_env_matching(test_env_request: Any, boardfarm_env: Any) -> bool:  # noqa: ANN401
    """Check test environment request is a subset of boardfarm environment.

    Recursively checks dictionaries for match. A value of None in the test
    environment request is used as a wildcard, i.e. matches any values.
    A list in test environment request is considered as options in boardfarm
    environment configuration.

    This function is ported from pytest-boardfarm to maintain compatibility.

    Args:
        test_env_request: Test environment request (dict, list, or scalar)
        boardfarm_env: Boardfarm environment data

    Returns:
        True if test environment requirements are met, otherwise False.

    Examples:
        >>> is_env_matching(None, "any_value")
        True
        >>> is_env_matching({"key": "value"}, {"key": "value", "other": "data"})
        True
        >>> is_env_matching(["opt1", "opt2"], "opt1")
        True
    """
    is_matching = False

    if test_env_request is None:
        is_matching = True
    elif (
        isinstance(test_env_request, dict)
        and isinstance(boardfarm_env, dict)
        and all(
            is_env_matching(v, boardfarm_env.get(k))
            for k, v in test_env_request.items()
        )
    ):
        is_matching = True
    elif (
        isinstance(test_env_request, list)
        and isinstance(boardfarm_env, (str, int, float, bool))
        and boardfarm_env in test_env_request
    ):
        is_matching = True
    elif (
        isinstance(boardfarm_env, list)
        and isinstance(test_env_request, (str, int, float, bool))
        and test_env_request in boardfarm_env
    ):
        is_matching = True
    elif (
        isinstance(test_env_request, dict)
        and isinstance(boardfarm_env, list)
        and any(is_env_matching(test_env_request, item) for item in boardfarm_env)
    ):
        is_matching = True
    elif (
        isinstance(test_env_request, list)
        and isinstance(boardfarm_env, list)
        and all(is_env_matching(item, boardfarm_env) for item in test_env_request)
    ):
        is_matching = True
    elif (
        isinstance(test_env_request, list)
        and isinstance(boardfarm_env, dict)
        and any(is_env_matching(item, boardfarm_env) for item in test_env_request)
    ):
        is_matching = True
    elif test_env_request == boardfarm_env:
        is_matching = True
    elif (
        isinstance(test_env_request, list)
        and isinstance(boardfarm_env, str)
        and all(
            isinstance(contains_check_dict, dict) and len(contains_check_dict) == 1
            for contains_check_dict in test_env_request
        )
    ):
        is_matching = _perform_contains_check(test_env_request, boardfarm_env)

    return is_matching


