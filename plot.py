# /// script
# requires-python = ">=3.10"
# dependencies = ["pygame-ce", "astral"]
# ///

"""Prepare the data and render one stargazing picture."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from fetch import FILE
from plot_data import load_observation, rows
from plot_render import render


HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"
PICTURE = "plot.png"
SPRITE = HERE / "sprites" / "cloud.png"
FONT_DIR = HERE / "fonts"
MINUTES_PER_STEP = 10
STEPS_PER_HOUR = 60 // MINUTES_PER_STEP


def interpolate_angle(start, end, fraction):
    difference = (end - start + 180) % 360 - 180
    return (start + difference * fraction) % 360


def interpolate_observation(start, end, fraction):
    time = start.time + timedelta(
        minutes=MINUTES_PER_STEP * round(fraction * STEPS_PER_HOUR)
    )
    return replace(
        start,
        time=time,
        readable_time=time.strftime("%I:%M %p").lstrip("0"),
        cloud_coverage=(
            start.cloud_coverage
            + (end.cloud_coverage - start.cloud_coverage) * fraction
        ),
        coverage_fraction=(
            start.coverage_fraction
            + (end.coverage_fraction - start.coverage_fraction) * fraction
        ),
        visibility_meters=(
            start.visibility_meters
            + (end.visibility_meters - start.visibility_meters) * fraction
        ),
        stargaze_score=(
            start.stargaze_score
            + (end.stargaze_score - start.stargaze_score) * fraction
        ),
        moon_phase=start.moon_phase + (end.moon_phase - start.moon_phase) * fraction,
        moon_illumination=(
            start.moon_illumination
            + (end.moon_illumination - start.moon_illumination) * fraction
        ),
        moon_altitude=(
            start.moon_altitude
            + (end.moon_altitude - start.moon_altitude) * fraction
        ),
        moon_azimuth=(
            interpolate_angle(start.moon_azimuth, end.moon_azimuth, fraction)
        ),
        sun_altitude=(
            start.sun_altitude
            + (end.sun_altitude - start.sun_altitude) * fraction
        ),
        sun_azimuth=(
            start.sun_azimuth
            + (end.sun_azimuth - start.sun_azimuth) * fraction
        ),
        daylight_brightness=(
            start.daylight_brightness
            + (end.daylight_brightness - start.daylight_brightness) * fraction
        ),
    )


def main():
    hourly_observations = [
        load_observation(DATA, row_index)
        for row_index in range(len(rows(DATA)))
    ]
    observations = []
    for index, observation in enumerate(hourly_observations):
        if index + 1 < len(hourly_observations):
            following = hourly_observations[index + 1]
            for step in range(STEPS_PER_HOUR):
                observations.append(
                    interpolate_observation(
                        observation, following, step / STEPS_PER_HOUR
                    )
                )
        else:
            observations.append(observation)
    render(observations, SPRITE, FONT_DIR, OUT / PICTURE, initial_index=44)


if __name__ == "__main__":
    main()
