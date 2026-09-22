"""Unit tests for tg_sticker.utils.logger."""

import logging

import pytest

from tg_sticker.utils.logger import (
    ColoredFormatter,
    get_logger,
    logger,
    print_divider,
    set_level,
)


def test_logger_methods(caplog):
    """Test logger methods emit records with proper levels."""
    with caplog.at_level(logging.DEBUG, logger="tg_sticker"):
        logger.debug("Debug message: %s", "test")
        logger.info("Info message: %d", 123)
        logger.warn("Warn message: %s", "warning")
        logger.warning("Warning message: %s", "warning2")
        logger.error("Error message: %s", "failure")

    messages = [rec.getMessage() for rec in caplog.records]
    assert "Debug message: test" in messages
    assert "Info message: 123" in messages
    assert "Warn message: warning" in messages
    assert "Warning message: warning2" in messages
    assert "Error message: failure" in messages


def test_set_level():
    """Test set_level changes logger level and rejects invalid levels."""
    set_level("DEBUG")
    log = get_logger("tg_sticker")
    assert log.level == logging.DEBUG

    set_level("INFO")
    assert log.level == logging.INFO

    with pytest.raises(ValueError, match="Unknown log level"):
        set_level("INVALID_LEVEL_NAME")


def test_print_divider(caplog):
    """Test print_divider outputs centered divider line."""
    with caplog.at_level(logging.INFO, logger="tg_sticker"):
        print_divider("Summary", length=40)
        logger.divider("Done", length=30)
        print_divider()

    messages = [rec.getMessage() for rec in caplog.records]
    assert any("Summary" in m for m in messages)
    assert any("Done" in m for m in messages)
    assert any("=" * 50 in m for m in messages)


def test_colored_formatter():
    """Test ColoredFormatter colors levelname when tty is active."""
    formatter = ColoredFormatter("%(levelname)s - %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "test message" in formatted
