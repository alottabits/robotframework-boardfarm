"""Robot Framework Boardfarm exceptions."""

from boardfarm3.exceptions import BoardfarmException


class BoardfarmRobotError(BoardfarmException):
    """Raise this on robotframework-boardfarm related errors."""


class BoardfarmListenerError(BoardfarmRobotError):
    """Raise this on listener lifecycle errors."""


class BoardfarmLibraryError(BoardfarmRobotError):
    """Raise this on keyword library errors."""


class DeviceNotInitializedError(BoardfarmRobotError):
    """Raise when devices are accessed before initialization."""


class EnvironmentMismatchError(BoardfarmRobotError):
    """Raise when test environment requirements are not met."""
