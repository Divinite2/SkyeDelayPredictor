"""Shared helpers: project paths and config loading. Everything internal is UTC."""
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=None)
def config() -> dict:
    return yaml.safe_load((ROOT / "config/config.yaml").read_text())


@lru_cache(maxsize=None)
def airport_tz() -> dict:
    return yaml.safe_load((ROOT / "config/airport_timezones.yaml").read_text())["airport_tz"]


def path(key: str) -> Path:
    """Resolve a `paths:` entry from config (absolute, or relative to the repo root)."""
    p = Path(config()["paths"][key])
    return p if p.is_absolute() else ROOT / p


def raw_csv() -> Path:
    local = ROOT / "data/raw/Flight_Data_With_Weather_Final.csv"
    return local if local.exists() else path("raw_csv")
