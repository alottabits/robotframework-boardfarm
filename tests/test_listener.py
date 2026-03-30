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

        assert listener.get_option("board_name") == "test-board"
        assert listener.get_option("env_config") == "/path/to/env.json"
        assert listener.get_option("inventory_config") == "/path/to/inv.json"
        assert listener.get_option("skip_boot") is True
        assert listener.get_option("skip_contingency_checks") is True

    def test_initialization_defaults(self) -> None:
        """Test listener initializes with default values."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        assert listener.get_option("board_name") == ""
        assert listener.get_option("skip_boot") is False
        assert listener.get_option("skip_contingency_checks") is False

    def test_initialization_creates_empty_teardown_stack(self) -> None:
        """Test that init creates an empty teardown stack."""
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            listener = BoardfarmListener()

        assert listener._teardown_stack == []

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


class TestTeardownStack:
    """Tests for the per-test teardown stack on BoardfarmListener."""

    @pytest.fixture()
    def listener(self) -> BoardfarmListener:
        with patch("robotframework_boardfarm.listener.get_plugin_manager"):
            return BoardfarmListener()

    def test_register_teardown_adds_to_stack(self, listener: BoardfarmListener) -> None:
        """Registered actions appear on the stack."""
        func = MagicMock()
        listener.register_teardown("desc", func, 1, key="val")

        assert len(listener._teardown_stack) == 1
        desc, fn, args, kwargs = listener._teardown_stack[0]
        assert desc == "desc"
        assert fn is func
        assert args == (1,)
        assert kwargs == {"key": "val"}

    def test_drain_executes_lifo(self, listener: BoardfarmListener) -> None:
        """Stack drains in LIFO order."""
        order: list[str] = []
        listener.register_teardown("first", lambda: order.append("first"))
        listener.register_teardown("second", lambda: order.append("second"))
        listener.register_teardown("third", lambda: order.append("third"))

        listener._drain_teardown_stack()

        assert order == ["third", "second", "first"]
        assert listener._teardown_stack == []

    def test_drain_passes_args(self, listener: BoardfarmListener) -> None:
        """Teardown callable receives the args captured at registration time."""
        func = MagicMock()
        listener.register_teardown("action", func, "a", "b", x=42)

        listener._drain_teardown_stack()

        func.assert_called_once_with("a", "b", x=42)

    def test_drain_continues_after_failure(self, listener: BoardfarmListener) -> None:
        """A failing teardown does not prevent subsequent teardowns."""
        first = MagicMock()
        failing = MagicMock(side_effect=RuntimeError("boom"))
        last = MagicMock()

        listener.register_teardown("first", first)
        listener.register_teardown("failing", failing)
        listener.register_teardown("last", last)

        listener._drain_teardown_stack()

        last.assert_called_once()
        failing.assert_called_once()
        first.assert_called_once()

    def test_drain_on_empty_stack_is_noop(self, listener: BoardfarmListener) -> None:
        """Draining an empty stack does nothing."""
        listener._drain_teardown_stack()
        assert listener._teardown_stack == []

    def test_end_test_drains_stack(self, listener: BoardfarmListener) -> None:
        """end_test drains the teardown stack."""
        func = MagicMock()
        listener.register_teardown("cleanup", func, 99)

        data = MagicMock()
        result = MagicMock()

        with patch.object(listener, "_refresh_cpe_console"):
            with patch.object(listener, "_clear_library_context"):
                listener.end_test(data, result)

        func.assert_called_once_with(99)
        assert listener._teardown_stack == []

    def test_end_test_calls_refresh_and_clear(
        self, listener: BoardfarmListener,
    ) -> None:
        """end_test invokes CPE console refresh and context clearing."""
        data = MagicMock()
        result = MagicMock()

        with patch.object(listener, "_refresh_cpe_console") as mock_refresh:
            with patch.object(listener, "_clear_library_context") as mock_clear:
                listener.end_test(data, result)

        mock_refresh.assert_called_once()
        mock_clear.assert_called_once()

    def test_refresh_cpe_console_no_device_manager(
        self, listener: BoardfarmListener,
    ) -> None:
        """_refresh_cpe_console is a no-op when device manager is None."""
        assert listener._device_manager is None
        listener._refresh_cpe_console()

    def test_refresh_cpe_console_with_cpe(
        self, listener: BoardfarmListener,
    ) -> None:
        """_refresh_cpe_console disconnects and reconnects."""
        mock_cpe = MagicMock()
        mock_cpe.device_name = "my-cpe"
        mock_dm = MagicMock()
        mock_dm.get_device_by_type.return_value = mock_cpe
        listener._device_manager = mock_dm

        with patch(
            "robotframework_boardfarm.listener.BoardfarmListener._refresh_cpe_console",
            wraps=listener._refresh_cpe_console,
        ):
            listener._refresh_cpe_console()

        mock_cpe.hw.disconnect_from_consoles.assert_called_once()
        mock_cpe.hw.connect_to_consoles.assert_called_once_with("my-cpe")

    def test_clear_library_context(self, listener: BoardfarmListener) -> None:
        """_clear_library_context calls clear_test_context on the library."""
        mock_lib = MagicMock()

        with patch(
            "robotframework_boardfarm.listener.BoardfarmListener._clear_library_context",
            wraps=listener._clear_library_context,
        ):
            with patch(
                "robot.libraries.BuiltIn.BuiltIn",
            ) as MockBuiltIn:
                MockBuiltIn.return_value.get_library_instance.return_value = mock_lib
                listener._clear_library_context()

        mock_lib.clear_test_context.assert_called_once()

    def test_clear_library_context_swallows_import_error(
        self, listener: BoardfarmListener,
    ) -> None:
        """_clear_library_context does not raise when Robot is not available."""
        with patch(
            "robotframework_boardfarm.listener.BoardfarmListener._clear_library_context",
            wraps=listener._clear_library_context,
        ):
            with patch.dict("sys.modules", {"robot.libraries.BuiltIn": None}):
                listener._clear_library_context()
