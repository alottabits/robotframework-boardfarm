"""Unit tests for UseCaseLibrary.

Tests the dynamic keyword discovery and execution from boardfarm3.use_cases.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestUseCaseLibraryDiscovery:
    """Tests for keyword discovery from use_cases modules."""

    def test_library_initialization(self) -> None:
        """Test library initializes without errors."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary()
        assert lib is not None
        assert lib.ROBOT_LIBRARY_SCOPE == "GLOBAL"

    def test_library_with_custom_modules(self) -> None:
        """Test library can be initialized with custom module list."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary(modules=["cpe", "acs"])
        assert lib._modules_to_load == ["cpe", "acs"]

    def test_library_with_excluded_modules(self) -> None:
        """Test library can exclude modules."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary(exclude_modules=["voice", "wifi"])
        assert "voice" in lib._exclude_modules
        assert "wifi" in lib._exclude_modules

    def test_lazy_discovery(self) -> None:
        """Test keywords are discovered lazily."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary()
        # Before accessing keywords, discovery hasn't happened
        assert not lib._discovered

    @patch("robotframework_boardfarm.use_case_library.importlib.import_module")
    def test_discover_keywords_from_module(self, mock_import: MagicMock) -> None:
        """Test keyword discovery from a mock module."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        # Create a mock module with some functions
        mock_module = MagicMock()
        mock_module.__name__ = "boardfarm3.use_cases.cpe"

        # Create mock functions
        def get_cpu_usage(board: Any) -> float:
            """Get CPU usage of CPE."""
            return 50.0

        def get_memory_usage(board: Any) -> dict[str, int]:
            """Get memory usage of CPE."""
            return {"total": 1000, "used": 500}

        def _private_function() -> None:
            """Private function that should be excluded."""
            pass

        # Set up the mock module
        mock_module.get_cpu_usage = get_cpu_usage
        mock_module.get_memory_usage = get_memory_usage
        mock_module._private_function = _private_function
        mock_module.__dict__ = {
            "get_cpu_usage": get_cpu_usage,
            "get_memory_usage": get_memory_usage,
            "_private_function": _private_function,
        }

        def mock_dir(obj: Any) -> list[str]:
            return ["get_cpu_usage", "get_memory_usage", "_private_function"]

        mock_import.return_value = mock_module

        lib = UseCaseLibrary(modules=["cpe"])

        with patch("builtins.dir", mock_dir):
            keywords = lib.get_keyword_names()

        # Should have discovered the public functions
        assert "Cpe Get Cpu Usage" in keywords
        assert "Cpe Get Memory Usage" in keywords
        # Private function should be excluded
        assert "_private_function" not in str(keywords).lower()


class TestUseCaseLibraryExecution:
    """Tests for keyword execution."""

    @patch("robotframework_boardfarm.use_case_library.importlib.import_module")
    def test_run_keyword(self, mock_import: MagicMock) -> None:
        """Test running a discovered keyword."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        # Create a mock function
        mock_func = MagicMock(return_value=42.0)
        mock_func.__module__ = "boardfarm3.use_cases.cpe"
        mock_func.__doc__ = "Get CPU usage"

        # Create mock module
        mock_module = MagicMock()
        mock_module.__name__ = "boardfarm3.use_cases.cpe"
        mock_module.get_cpu_usage = mock_func

        def mock_dir(obj: Any) -> list[str]:
            if obj == mock_module:
                return ["get_cpu_usage"]
            return []

        mock_import.return_value = mock_module

        lib = UseCaseLibrary(modules=["cpe"])

        with patch("builtins.dir", mock_dir):
            lib._discover_keywords()
            result = lib.run_keyword("Cpe Get Cpu Usage", [MagicMock()], {})

        assert result == 42.0
        mock_func.assert_called_once()

    def test_run_unknown_keyword_raises(self) -> None:
        """Test running unknown keyword raises error."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary(modules=[])  # No modules = no keywords
        lib._discovered = True  # Skip discovery

        with pytest.raises(ValueError, match="Unknown keyword"):
            lib.run_keyword("Unknown Keyword", [], {})


class TestUseCaseLibraryDocumentation:
    """Tests for keyword documentation."""

    def test_intro_documentation(self) -> None:
        """Test __intro__ returns library docstring."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary()
        doc = lib.get_keyword_documentation("__intro__")

        assert "Dynamic library" in doc
        assert "use_cases" in doc

    @patch("robotframework_boardfarm.use_case_library.importlib.import_module")
    def test_keyword_documentation(self, mock_import: MagicMock) -> None:
        """Test keyword documentation includes docstring."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        # Create mock function with docstring
        def mock_func(board: Any) -> float:
            """Get the CPU usage of the CPE device.

            This is a detailed description.
            """
            return 50.0

        mock_func.__module__ = "boardfarm3.use_cases.cpe"

        mock_module = MagicMock()
        mock_module.__name__ = "boardfarm3.use_cases.cpe"
        mock_module.get_cpu_usage = mock_func

        def mock_dir(obj: Any) -> list[str]:
            if obj == mock_module:
                return ["get_cpu_usage"]
            return []

        mock_import.return_value = mock_module

        lib = UseCaseLibrary(modules=["cpe"])

        with patch("builtins.dir", mock_dir):
            lib._discover_keywords()
            doc = lib.get_keyword_documentation("Cpe Get Cpu Usage")

        assert "CPU usage" in doc
        assert "boardfarm3.use_cases.cpe" in doc


class TestUseCaseLibraryArguments:
    """Tests for keyword argument handling."""

    @patch("robotframework_boardfarm.use_case_library.importlib.import_module")
    def test_keyword_arguments(self, mock_import: MagicMock) -> None:
        """Test keyword arguments are extracted correctly."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        # Create mock function with arguments
        def mock_func(board: Any, timeout: int = 30, via: str = "nbi") -> float:
            """Mock function."""
            return 50.0

        mock_func.__module__ = "boardfarm3.use_cases.cpe"

        mock_module = MagicMock()
        mock_module.__name__ = "boardfarm3.use_cases.cpe"
        mock_module.test_func = mock_func

        def mock_dir(obj: Any) -> list[str]:
            if obj == mock_module:
                return ["test_func"]
            return []

        mock_import.return_value = mock_module

        lib = UseCaseLibrary(modules=["cpe"])

        with patch("builtins.dir", mock_dir):
            lib._discover_keywords()
            args = lib.get_keyword_arguments("Cpe Test Func")

        assert "board" in args
        assert "timeout=30" in args
        assert "via='nbi'" in args


class TestUseCaseLibraryTags:
    """Tests for keyword tagging."""

    @patch("robotframework_boardfarm.use_case_library.importlib.import_module")
    def test_keyword_tags(self, mock_import: MagicMock) -> None:
        """Test keywords are tagged with their module name."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        mock_func = MagicMock(return_value=50.0)
        mock_func.__module__ = "boardfarm3.use_cases.acs"
        mock_func.__doc__ = "Test function"

        mock_module = MagicMock()
        mock_module.__name__ = "boardfarm3.use_cases.acs"
        mock_module.get_value = mock_func

        def mock_dir(obj: Any) -> list[str]:
            if obj == mock_module:
                return ["get_value"]
            return []

        mock_import.return_value = mock_module

        lib = UseCaseLibrary(modules=["acs"])

        with patch("builtins.dir", mock_dir):
            lib._discover_keywords()
            tags = lib.get_keyword_tags("Acs Get Value")

        assert "use_case:acs" in tags


class TestUseCaseLibraryIntegration:
    """Integration tests that may require actual boardfarm3 import."""

    @pytest.mark.skipif(
        not pytest.importorskip("boardfarm3", reason="boardfarm3 not available"),
        reason="boardfarm3 not available",
    )
    def test_real_module_discovery(self) -> None:
        """Test discovery with real boardfarm3.use_cases modules."""
        from robotframework_boardfarm.use_case_library import UseCaseLibrary

        lib = UseCaseLibrary()
        keywords = lib.get_keyword_names()

        # Should have discovered keywords from multiple modules
        assert len(keywords) > 0

        # Check for expected patterns
        keyword_str = " ".join(keywords)
        # Should have Cpe, Acs, etc. prefixes
        assert any(kw.startswith("Cpe") for kw in keywords) or "cpe" in keyword_str.lower()
