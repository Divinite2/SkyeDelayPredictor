"""Back-end selection (BACKEND=mock|real). Returns a predict() that never raises.

Real responses are passed to the screen exactly as received: no re-stamping, no edits
(lead note F-b). Re-stamping exists only inside frontend/mock_backend.py.
"""
from __future__ import annotations

import os
from typing import Callable

Predict = Callable[[str, str, str], dict]


def _error(code: str, message: str, airport=None, target=None, now=None) -> dict:
    """Contract-shaped error response (schema v1.0, status 'error')."""
    return {"schema_version": "1.0", "status": "error",
            "request": {"airport": airport, "target_hour_utc": target,
                        "now_utc": now, "lead_time_h": None},
            "refusal": None, "error": {"code": code, "message": message}}


def backend_mode() -> str:
    return "real" if os.getenv("BACKEND", "mock").strip().lower() == "real" else "mock"


def load_predict(mode: str | None = None) -> Predict:
    """Import the chosen back end. If the import fails, return a predict() that always
    yields the error card instead of crashing the page (F3.3)."""
    mode = mode or backend_mode()
    try:
        if mode == "real":
            from backend.api import predict as raw
        else:
            from frontend.mock_backend import predict as raw
    except Exception as exc:  # ImportError, missing model files, etc.
        msg = f"Back end could not be loaded ({mode}): {type(exc).__name__}: {exc}"

        def unavailable(airport, target_hour_utc, now_utc):
            return _error("BACKEND_UNAVAILABLE", msg, airport, target_hour_utc, now_utc)
        return unavailable

    def safe_predict(airport: str, target_hour_utc: str, now_utc: str) -> dict:
        try:
            return raw(airport, target_hour_utc, now_utc)   # returned untouched
        except Exception as exc:  # contract says never raises; guard anyway
            return _error("BACKEND_EXCEPTION", f"{type(exc).__name__}: {exc}",
                          airport, target_hour_utc, now_utc)
    return safe_predict
