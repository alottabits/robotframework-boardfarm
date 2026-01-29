"""Unit tests for BoardfarmListener."""

from unittest.mock import MagicMock, patch

import pytest

from robotframework_boardfarm.listener import BoardfarmListener


class TestBoardfarmListener:
    """Tests for BoardfarmListener class."""

    def test_initialization(self) -> None:
        """Test listener initializes with provided arguments."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener(
                board_name="test-board",
                env_config="/path/to/env.json",
                inventory_config="/path/to/inv.json",
                skip_boot="true",
                skip_contingency_checks="true",
            )

        assert listener._board_name == "test-board"
        assert listener._env_config_path == "/path/to/env.json"
        assert listener._inventory_config_path == "/path/to/inv.json"
        assert listener._skip_boot is True
        assert listener._skip_contingency_checks is True

    def test_initialization_defaults(self) -> None:
        """Test listener initializes with default values."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        assert listener._board_name == ""
        assert listener._skip_boot is False
        assert listener._skip_contingency_checks is False

    def test_cmdline_args_property(self) -> None:
        """Test cmdline_args property returns correct Namespace."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener(
                board_name="test-board",
                env_config="/path/to/env.json",
                inventory_config="/path/to/inv.json",
            )

        args = listener.cmdline_args
        assert args.board_name == "test-board"
        assert args.env_config == "/path/to/env.json"
        assert args.inventory_config == "/path/to/inv.json"

    def test_parse_env_req_tags_json(self) -> None:
        """Test parsing JSON env_req tags."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        tags = ['env_req:{"key": "value"}', "other_tag"]
        result = listener._parse_env_req_tags(tags)
        assert result == {"key": "value"}

    def test_parse_env_req_tags_preset(self) -> None:
        """Test parsing preset env_req tags."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        tags = ["env_req:dual_stack", "other_tag"]
        result = listener._parse_env_req_tags(tags)
        assert "environment_def" in result
        assert "board" in result["environment_def"]

    def test_parse_env_req_tags_no_match(self) -> None:
        """Test parsing tags with no env_req."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        tags = ["other_tag", "another_tag"]
        result = listener._parse_env_req_tags(tags)
        assert result is None

    def test_get_env_req_preset(self) -> None:
        """Test getting preset environment requirements."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        dual_stack = listener._get_env_req_preset("dual_stack")
        assert dual_stack["environment_def"]["board"]["eRouter_Provisioning_mode"] == [
            "dual"
        ]

        ipv4_only = listener._get_env_req_preset("ipv4_only")
        assert ipv4_only["environment_def"]["board"]["eRouter_Provisioning_mode"] == [
            "ipv4"
        ]

        unknown = listener._get_env_req_preset("unknown_preset")
        assert unknown == {}

    def test_device_manager_not_initialized(self) -> None:
        """Test accessing device_manager before deployment raises error."""
        from robotframework_boardfarm.exceptions import DeviceNotInitializedError

        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        with pytest.raises(DeviceNotInitializedError):
            _ = listener.device_manager

    def test_boardfarm_config_not_initialized(self) -> None:
        """Test accessing boardfarm_config before deployment raises error."""
        from robotframework_boardfarm.exceptions import DeviceNotInitializedError

        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        with pytest.raises(DeviceNotInitializedError):
            _ = listener.boardfarm_config
