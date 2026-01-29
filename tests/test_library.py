"""Unit tests for BoardfarmLibrary."""

from unittest.mock import MagicMock, patch

import pytest

from robotframework_boardfarm.library import BoardfarmLibrary


class TestBoardfarmLibrary:
    """Tests for BoardfarmLibrary class."""

    def test_initialization(self) -> None:
        """Test library initializes correctly."""
        lib = BoardfarmLibrary()
        assert lib._context == {}
        assert lib._device_type_cache == {}

    def test_set_and_get_test_context(self) -> None:
        """Test setting and getting test context."""
        lib = BoardfarmLibrary()
        lib.set_test_context("key", "value")
        assert lib.get_test_context("key") == "value"

    def test_get_test_context_default(self) -> None:
        """Test getting context with default value."""
        lib = BoardfarmLibrary()
        assert lib.get_test_context("missing", "default") == "default"
        assert lib.get_test_context("missing") is None

    def test_clear_test_context(self) -> None:
        """Test clearing test context."""
        lib = BoardfarmLibrary()
        lib.set_test_context("key1", "value1")
        lib.set_test_context("key2", "value2")
        lib.clear_test_context()
        assert lib.get_test_context("key1") is None
        assert lib.get_test_context("key2") is None

    def test_log_step(self) -> None:
        """Test log_step keyword."""
        lib = BoardfarmLibrary()
        with patch("robotframework_boardfarm.library.logger") as mock_logger:
            lib.log_step("Test step message")
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "[STEP] Test step message" in call_args[0][0]

    def test_get_env_req_preset(self) -> None:
        """Test getting preset environment requirements."""
        lib = BoardfarmLibrary()

        dual_stack = lib._get_env_req_preset("dual_stack")
        assert dual_stack["environment_def"]["board"]["eRouter_Provisioning_mode"] == [
            "dual"
        ]

        ipv4_only = lib._get_env_req_preset("ipv4_only")
        assert ipv4_only["environment_def"]["board"]["eRouter_Provisioning_mode"] == [
            "ipv4"
        ]

        ipv6_only = lib._get_env_req_preset("ipv6_only")
        assert ipv6_only["environment_def"]["board"]["eRouter_Provisioning_mode"] == [
            "ipv6"
        ]

    def test_import_class(self) -> None:
        """Test _import_class static method."""
        lib = BoardfarmLibrary()
        # Import a known class
        result = lib._import_class("json.JSONEncoder")
        import json

        assert result is json.JSONEncoder

    def test_resolve_device_type_caching(self) -> None:
        """Test that device type resolution uses cache."""
        lib = BoardfarmLibrary()
        # Manually add to cache
        mock_type = type("MockDevice", (), {})
        lib._device_type_cache["MockDevice"] = mock_type

        result = lib._resolve_device_type("MockDevice")
        assert result is mock_type


class TestBoardfarmLibraryWithListener:
    """Tests for BoardfarmLibrary keywords that require listener."""

    def test_get_device_manager_no_listener(self) -> None:
        """Test get_device_manager raises error without listener."""
        from robotframework_boardfarm.exceptions import BoardfarmListenerError

        lib = BoardfarmLibrary()

        # Patch the listener getter to raise error
        with patch(
            "robotframework_boardfarm.library.BoardfarmLibrary._get_listener",
            side_effect=BoardfarmListenerError("No listener"),
        ):
            with pytest.raises(BoardfarmListenerError):
                lib.get_device_manager()

    def test_get_boardfarm_config_with_listener(self) -> None:
        """Test get_boardfarm_config with mocked listener."""
        lib = BoardfarmLibrary()

        mock_config = MagicMock()
        mock_listener = MagicMock()
        mock_listener.boardfarm_config = mock_config

        with patch.object(lib, "_get_listener", return_value=mock_listener):
            result = lib.get_boardfarm_config()
            assert result is mock_config

    def test_get_provisioning_mode_with_listener(self) -> None:
        """Test get_provisioning_mode with mocked listener."""
        lib = BoardfarmLibrary()

        mock_config = MagicMock()
        mock_config.get_prov_mode.return_value = "dual"
        mock_listener = MagicMock()
        mock_listener.boardfarm_config = mock_config

        with patch.object(lib, "_get_listener", return_value=mock_listener):
            result = lib.get_provisioning_mode()
            assert result == "dual"
