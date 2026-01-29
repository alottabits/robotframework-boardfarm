"""Unit tests for robotframework_boardfarm.utils module."""

import pytest

from robotframework_boardfarm.utils import ContextStorage, is_env_matching


class TestIsEnvMatching:
    """Tests for is_env_matching function."""

    def test_none_matches_anything(self) -> None:
        """None in test request matches any value."""
        assert is_env_matching(None, "any_value") is True
        assert is_env_matching(None, {"key": "value"}) is True
        assert is_env_matching(None, [1, 2, 3]) is True

    def test_exact_match(self) -> None:
        """Exact values match."""
        assert is_env_matching("value", "value") is True
        assert is_env_matching(123, 123) is True
        assert is_env_matching("value", "other") is False

    def test_dict_subset_match(self) -> None:
        """Dict in test request matches if subset of boardfarm env."""
        test_req = {"key": "value"}
        bf_env = {"key": "value", "other": "data"}
        assert is_env_matching(test_req, bf_env) is True

        test_req = {"key": "value", "missing": "key"}
        assert is_env_matching(test_req, bf_env) is False

    def test_list_options_match(self) -> None:
        """List in test request matches if boardfarm env is in the list."""
        test_req = ["opt1", "opt2", "opt3"]
        assert is_env_matching(test_req, "opt1") is True
        assert is_env_matching(test_req, "opt2") is True
        assert is_env_matching(test_req, "opt4") is False

    def test_boardfarm_env_list_match(self) -> None:
        """Scalar in test request matches if in boardfarm env list."""
        bf_env = ["opt1", "opt2", "opt3"]
        assert is_env_matching("opt1", bf_env) is True
        assert is_env_matching("opt4", bf_env) is False

    def test_nested_dict_match(self) -> None:
        """Nested dictionaries match recursively."""
        test_req = {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": ["dual"]},
            },
        }
        bf_env = {
            "environment_def": {
                "board": {
                    "eRouter_Provisioning_mode": "dual",
                    "model": "TestModel",
                },
            },
            "other_key": "value",
        }
        assert is_env_matching(test_req, bf_env) is True

    def test_nested_dict_no_match(self) -> None:
        """Nested dictionaries don't match when values differ."""
        test_req = {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": ["ipv4"]},
            },
        }
        bf_env = {
            "environment_def": {
                "board": {"eRouter_Provisioning_mode": "dual"},
            },
        }
        assert is_env_matching(test_req, bf_env) is False


class TestContextStorage:
    """Tests for ContextStorage class."""

    def test_set_and_get(self) -> None:
        """Test setting and getting values."""
        ctx = ContextStorage()
        ctx["key"] = "value"
        assert ctx["key"] == "value"

    def test_get_with_default(self) -> None:
        """Test get with default value."""
        ctx = ContextStorage()
        assert ctx.get("missing", "default") == "default"
        assert ctx.get("missing") is None

    def test_contains(self) -> None:
        """Test contains check."""
        ctx = ContextStorage()
        ctx["key"] = "value"
        assert "key" in ctx
        assert "missing" not in ctx

    def test_clear(self) -> None:
        """Test clearing context."""
        ctx = ContextStorage()
        ctx["key1"] = "value1"
        ctx["key2"] = "value2"
        ctx.clear()
        assert "key1" not in ctx
        assert "key2" not in ctx

    def test_items_keys_values(self) -> None:
        """Test items, keys, values methods."""
        ctx = ContextStorage()
        ctx["key1"] = "value1"
        ctx["key2"] = "value2"
        assert set(ctx.keys()) == {"key1", "key2"}
        assert set(ctx.values()) == {"value1", "value2"}
        assert dict(ctx.items()) == {"key1": "value1", "key2": "value2"}
