"""Load the generated weather data and prepare one observation for rendering."""

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


TIMEZONE = "HKT"
HKT = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Observation:
    time: datetime
    readable_time: str
    cloud_coverage: float
    coverage_fraction: float
    visibility: str
    stargaze_score: float
    moon_phase: float
    moon_illumination: float
    moon_altitude: float
    moon_azimuth: float
    moon_name: str
    sun_altitude: float
    sun_azimuth: float
    daylight_brightness: float


def rows(path):
    """Read hourly cloud coverage from the generated CSV."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def format_visibility(meters):
    if meters >= 1000:
        return f"{meters / 1000:.2f}".rstrip("0").rstrip(".") + " km"
    return f"{meters:.0f} m"


def lerp_color(start, end, amount):
    return tuple(
        start_channel + (end_channel - start_channel) * amount
        for start_channel, end_channel in zip(start, end)
    )


def load_observation(path, row_index=None):
    table = rows(path)
    sunrise = datetime.fromisoformat(table[0]["sunrise"]).replace(tzinfo=HKT)
    sunset = datetime.fromisoformat(table[0]["sunset"]).replace(tzinfo=HKT)
    selected = (
        table[row_index]
        if row_index is not None
        else max(table, key=lambda row: float(row["stargaze_score"]))
    )
    observation_time = datetime.fromisoformat(selected["time"]).replace(tzinfo=HKT)
    daylight_progress = (
        (observation_time - sunrise).total_seconds()
        / (sunset - sunrise).total_seconds()
    )
    daylight_brightness = (
        math.sin(math.pi * daylight_progress)
        if 0 <= daylight_progress <= 1
        else 0
    )
    cloud_coverage = float(selected["cloud_coverage"])

    return Observation(
        time=observation_time,
        readable_time=observation_time.strftime("%I:%M %p").lstrip("0"),
        cloud_coverage=cloud_coverage,
        coverage_fraction=max(0, min(cloud_coverage, 100)) / 100,
        visibility=format_visibility(float(selected["visibility"])),
        stargaze_score=float(selected["stargaze_score"]),
        moon_phase=float(selected["moon_phase"]),
        moon_illumination=float(selected["moon_illumination"]),
        moon_altitude=float(selected["moon_altitude"]),
        moon_azimuth=float(selected["moon_azimuth"]),
        moon_name=selected["moon_name"],
        sun_altitude=float(selected["sun_altitude"]),
        sun_azimuth=float(selected["sun_azimuth"]),
        daylight_brightness=daylight_brightness,
    )
