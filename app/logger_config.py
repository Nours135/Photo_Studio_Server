import json
import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


LOG_DIR = Path("./logs")
LOG_STRUCTURED = True
ROOT_LOG_LEVEL = "INFO"
CONSOLE_LEVEL = "INFO"
FILE_LEVEL = "DEBUG"
APP_LOG_MAX_BYTES = 10 * 1024 * 1024
APP_LOG_BACKUP_COUNT = 5
ERROR_LOG_MAX_BYTES = 50 * 1024 * 1024
ERROR_LOG_BACKUP_COUNT = 10
UVICORN_ACCESS_LEVEL = "WARNING"
UVICORN_ERROR_LEVEL = "INFO"

LOG_DIR.mkdir(parents=True, exist_ok=True)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
TEXT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - trace_id=%(trace_id)s - [%(filename)s:%(lineno)d] - %(message)s"

_RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)

def set_trace_id(value: str) -> None:
    _trace_id.set(value)

def clear_trace_id() -> None:
    _trace_id.set(None)

def get_trace_id() -> str | None:
    return _trace_id.get()


def _coerce_json_value(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS:
                log_entry[key] = _coerce_json_value(value)

        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "unknown"
        return True



def _build_formatter() -> logging.Formatter:
    if LOG_STRUCTURED:
        return JsonFormatter(datefmt=DATE_FORMAT)
    return logging.Formatter(TEXT_LOG_FORMAT, DATE_FORMAT)


def setup_logger() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(ROOT_LOG_LEVEL)
    root_logger.handlers.clear()
    root_logger.filters.clear()
    root_logger.addFilter(ContextFilter())

    formatter = _build_formatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(CONSOLE_LEVEL)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=APP_LOG_MAX_BYTES,
        backupCount=APP_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(FILE_LEVEL)
    file_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=ERROR_LOG_MAX_BYTES,
        backupCount=ERROR_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    for handler in (console_handler, file_handler, error_handler):
        handler.addFilter(ContextFilter())

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("uvicorn.access").setLevel(UVICORN_ACCESS_LEVEL)
    logging.getLogger("uvicorn.error").setLevel(UVICORN_ERROR_LEVEL)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


setup_logger()


if __name__ == "__main__":
    from uuid import uuid4

    set_trace_id(uuid4().hex)
    demo_logger = get_logger("logger_demo")
    demo_logger.info(
        "Structured logging example",
        extra={"event": "demo_run", "request_id": "req-12345", "user_id": "user-42"},
    )

    try:
        raise ValueError("Demo exception message for logging showcase")
    except ValueError:
        demo_logger.exception("Captured demo exception", extra={"event": "demo_exception"})
    finally:
        clear_trace_id()
