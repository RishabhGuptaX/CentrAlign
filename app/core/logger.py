"""Structured execution logging."""

from datetime import datetime


def log_event(event_type: str, message: str, **metadata):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "message": message,
        "metadata": metadata,
    }
