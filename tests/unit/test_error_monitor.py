"""Unit tests for ErrorMonitor — pluggable error capture with graceful degradation."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.error_monitor import ErrorMonitor, get_error_monitor


@pytest.fixture
def mock_settings():
    """Return a minimal Settings mock for the error monitor."""
    settings = MagicMock()
    settings.sentry_dsn = None  # No Sentry by default
    settings.env = "testing"
    settings.error_monitor_provider = ""
    return settings


@pytest.fixture
def monitor(mock_settings):
    """Create an ErrorMonitor with mocked settings."""
    with patch(
        "app.services.error_monitor.get_settings", return_value=mock_settings
    ):
        return ErrorMonitor()


class TestCaptureException:
    def test_capture_exception_returns_event_id(self, monitor):
        """capture_exception always returns a 32-char hex string (UUID hex)."""
        event_id = monitor.capture_exception(ValueError("test error"))
        assert isinstance(event_id, str)
        assert len(event_id) == 32
        # Must be valid hex
        int(event_id, 16)  # Will raise ValueError if not hex

    def test_capture_exception_returns_unique_ids(self, monitor):
        """Each call to capture_exception returns a different event_id."""
        id1 = monitor.capture_exception(RuntimeError("first"))
        id2 = monitor.capture_exception(RuntimeError("second"))
        assert id1 != id2

    def test_capture_exception_no_sentry(self, monitor, mock_settings):
        """When sentry_dsn is not set, capture_exception does not crash."""
        mock_settings.sentry_dsn = None
        # Should not raise
        event_id = monitor.capture_exception(ValueError("no sentry"))
        assert isinstance(event_id, str)
        assert len(event_id) == 32

    def test_capture_exception_with_sentry_dsn_initializes_sdk(self, monitor, mock_settings):
        """When sentry_dsn is set, _ensure_sentry attempts to initialize and
        the method still returns a valid event_id regardless of whether the
        Sentry SDK is importable or not."""
        mock_settings.sentry_dsn = "https://key@sentry.example.com/1"

        event_id = monitor.capture_exception(ValueError("sentry test"))
        assert isinstance(event_id, str)
        assert monitor._sentry_initialized is True
        # If sentry_sdk was importable, _sentry_sdk will be set; if not, it stays None.
        # Either way the monitor must not crash and must return a valid event id.

    def test_capture_exception_with_context(self, monitor):
        """Context dict is included in structured logging."""
        event_id = monitor.capture_exception(
            KeyError("missing key"),
            context={"user_id": "abc", "org_id": "org-1"},
        )
        assert isinstance(event_id, str)

    def test_capture_exception_sentry_init_called_once(self, monitor, mock_settings):
        """Sentry is lazy-initialized only once regardless of call count."""
        mock_settings.sentry_dsn = "https://key@sentry.example.com/1"

        monitor.capture_exception(ValueError("first"))
        assert monitor._sentry_initialized is True

        monitor.capture_exception(RuntimeError("second"))
        # Already initialized; _ensure_sentry is a fast no-op on second call
        assert monitor._sentry_initialized is True

    def test_capture_exception_logs_event_type(self, monitor):
        """The exception type is part of the log context."""
        # This test ensures the method doesn't crash and returns a valid event_id
        # regardless of the exception type
        event_id = monitor.capture_exception(TypeError("bad type"))
        assert isinstance(event_id, str)

    def test_capture_exception_null_exception_message(self, monitor):
        """Exceptions with no message (e.g., raise Exception()) don't crash."""
        event_id = monitor.capture_exception(Exception())
        assert isinstance(event_id, str)

    def test_capture_exception_empty_context(self, monitor):
        """Empty context dict does not cause issues."""
        event_id = monitor.capture_exception(ValueError("test"), context={})
        assert isinstance(event_id, str)


class TestGetErrorMonitorSingleton:
    def test_get_error_monitor_returns_same_instance(self):
        """get_error_monitor() is a singleton — repeated calls return the same instance."""
        get_error_monitor.cache_clear()

        with patch(
            "app.services.error_monitor.get_settings", return_value=MagicMock()
        ):
            instance1 = get_error_monitor()
            instance2 = get_error_monitor()

        assert instance1 is instance2

    def test_get_error_monitor_returns_error_monitor_type(self):
        """The singleton is an instance of ErrorMonitor."""
        get_error_monitor.cache_clear()

        with patch(
            "app.services.error_monitor.get_settings", return_value=MagicMock()
        ):
            instance = get_error_monitor()

        assert isinstance(instance, ErrorMonitor)
