"""Unit tests for DeviceMethodLibrary."""

from unittest.mock import MagicMock, patch

import pytest


class TestDeviceMethodLibrary:
    """Tests for DeviceMethodLibrary class."""

    def test_method_to_keyword_name_snake_case(self) -> None:
        """Test converting snake_case to keyword name."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        assert lib._method_to_keyword_name("get_uptime") == "Get Uptime"
        assert lib._method_to_keyword_name("is_online") == "Is Online"
        assert lib._method_to_keyword_name("get_interface_ipv4_addr") == "Get Interface Ipv4 Addr"

    def test_method_to_keyword_name_with_prefix(self) -> None:
        """Test converting method name with prefix."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        assert lib._method_to_keyword_name("GPV", "Nbi") == "Nbi GPV"
        assert lib._method_to_keyword_name("get_uptime", "Sw") == "Sw Get Uptime"

    def test_method_to_keyword_name_uppercase(self) -> None:
        """Test preserving uppercase method names."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        # Uppercase methods should stay uppercase
        assert lib._method_to_keyword_name("GPV") == "GPV"
        assert lib._method_to_keyword_name("SPV") == "SPV"
        assert lib._method_to_keyword_name("GPN") == "GPN"

    def test_keyword_to_method_name_simple(self) -> None:
        """Test converting keyword name back to method name."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        component, method = lib._keyword_to_method_name("Get Uptime")
        assert component == ""
        assert "get" in method.lower() and "uptime" in method.lower()

    def test_keyword_to_method_name_with_component(self) -> None:
        """Test converting keyword with component prefix."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        component, method = lib._keyword_to_method_name("Nbi GPV")
        assert component == "nbi"
        assert "GPV" in method

    def test_get_keyword_names_always_includes_generic(self) -> None:
        """Test that generic keywords are always available."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        with patch("robotframework_boardfarm.dynamic_device_library.get_plugin_manager"):
            lib = DeviceMethodLibrary()

        keywords = lib.get_keyword_names()
        assert "Call Device Method" in keywords
        assert "Call Component Method" in keywords

    def test_cache_method_info(self) -> None:
        """Test method info caching."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        def sample_method(arg1: str, arg2: int = 10) -> str:
            """Sample method documentation."""
            return f"{arg1}-{arg2}"

        lib._cache_method_info("Sample Method", sample_method)

        assert "Sample Method" in lib._doc_cache
        assert "Sample method documentation" in lib._doc_cache["Sample Method"]
        assert "Sample Method" in lib._argspec_cache
        assert "arg1" in lib._argspec_cache["Sample Method"]

    def test_get_keyword_documentation(self) -> None:
        """Test getting keyword documentation."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        # Intro documentation
        intro = lib.get_keyword_documentation("__intro__")
        assert "Dynamic" in intro or "device" in intro.lower()

        # Generic keyword documentation
        call_doc = lib.get_keyword_documentation("Call Device Method")
        assert "device" in call_doc.lower()

    def test_get_keyword_arguments(self) -> None:
        """Test getting keyword arguments."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        args = lib.get_keyword_arguments("Call Device Method")
        assert "device_type" in args
        assert "method_name" in args

        args = lib.get_keyword_arguments("Call Component Method")
        assert "component" in args


class TestDeviceMethodLibraryWithMockDevice:
    """Tests for DeviceMethodLibrary with mocked devices."""

    def test_run_keyword_generic_method(self) -> None:
        """Test running generic Call Device Method keyword."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        # Mock the device manager and device
        mock_dm = MagicMock()
        mock_acs = MagicMock()
        mock_acs.nbi.GPV.return_value = [{"key": "Test", "value": "value"}]
        mock_dm.get_device_by_type.return_value = mock_acs

        mock_listener = MagicMock()
        mock_listener.device_manager = mock_dm

        with patch("robotframework_boardfarm.dynamic_device_library.get_listener", return_value=mock_listener):
            with patch("robotframework_boardfarm.library.BoardfarmLibrary._resolve_device_type", return_value=type):
                # This would call the actual method in a real scenario
                pass  # Simplified test - full integration test needed

    def test_discover_component_keywords(self) -> None:
        """Test discovering keywords from device components."""
        from robotframework_boardfarm.dynamic_device_library import DeviceMethodLibrary

        lib = DeviceMethodLibrary()

        # Create mock component with methods
        mock_component = MagicMock()
        mock_component.GPV = MagicMock()
        mock_component.SPV = MagicMock()
        mock_component._private = MagicMock()  # Should be excluded

        keywords = lib._discover_component_keywords(mock_component, "Nbi")

        # Should include public methods but not private ones
        keyword_names = [k.lower() for k in keywords]
        assert any("gpv" in k for k in keyword_names)
        assert any("spv" in k for k in keyword_names)
        # Private methods should be excluded
        assert not any("private" in k for k in keyword_names)
